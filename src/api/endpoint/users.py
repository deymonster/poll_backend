from typing import List, Optional
from urllib.parse import urlparse
from core.local_config import settings

from fastapi import APIRouter, Depends, Body, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr

from sqlalchemy.orm import Session
from fastapi import Request
from starlette.responses import JSONResponse

from base.schemas import Message, TokenVerificationResponse, AvatarUpload
from company.service import delete_invitation, get_invitation_by_token, change_invitation_status
from core import config
from core.security import get_password_hash
from utils import send_new_account_email, generate_registration_token, verify_registration_token, \
    send_new_account_complete_registration_email
from api.utils.db import get_db
from api.utils.security import get_current_active_user, get_current_user_with_roles, get_current_user

from user.models import User as DBUser, UserRole
from user.schemas import User, UserCreate, UserUpdate, TokenData, RegistrationCompletion, UserCreateByEmail, UpdateUserProfile
from user.service import crud_user
from fastapi import BackgroundTasks
from api.utils.logger import PollLogger
from core.exceptions import TokenError, TokenExpiredError, CustomInvalidTokenError, NoInvitiationError

# Logging
logger = PollLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[User])
def read_users(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user)):
    """
    Получение списка пользователей

    :param db: Сессия базы данных
    :param skip: Количество пропускаемых записей
    :param limit: Количество возвращаемых записей
    :param current_user: Текущий пользователь с ролью суперпользователя
    :return: Список пользователей
    """
    # Проверяем роли - допускаются только SUPERADMIN и ADMIN
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])
    # Передаем текущего пользователя с ролью в метод get_multi
    users = crud_user.get_multi(db, current_user=current_user, skip=skip, limit=limit)
    return users


# endpoint for pre-registration user
@router.post("/register", response_model=Message)
def pre_register_user(
        *,
        request: Request,
        db: Session = Depends(get_db),
        user_in: UserCreateByEmail,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user)
):
    """
    Эндпойнт для регистрации пользователя.

    :param request Request from client
    :param db: Сессия базы данных
    :param user_in: Данные для создания пользователя
    :param background_tasks: BackgroundTasks
    :param current_user: Текущий пользователь с любой ролью
    :return: Сообщение об успешной предварительной регистрации

    Пример схемы для регистрации пользователя
    {
    "email": "popov@nitshop.ru",
    "full_name": "Попов Дмитрий",
    "roles": ["ADMIN", "USER"],
    "company_id": 1

    }
    """
    # restrict access for superadmin and admin
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])

    try:
        crud_user.register_user(db_session=db,
                                request=request,
                                current_user=current_user,
                                obj_in=user_in,
                                background_tasks=background_tasks)

        return JSONResponse(status_code=201, content={"message": "Email was sent to user"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})


# endpoint for verification registration token
@router.post("/register/verify", response_model=TokenVerificationResponse)
def verify_token(token_data: TokenData,
                 db: Session = Depends(get_db)):
    """ Эндпойнт для проверки токена регистрации

    :param token_data: Схема для проверки токена регистрации
    :param db: Session
    :return возвращает сообщение о валидности токена
    Пример тела запроса:
    {
    "token": "{token}"
    }
    """
    try:
        email, roles, full_name, company_id = verify_registration_token(token_data.token)
        invitation = get_invitation_by_token(db, token_data.token)

        if not invitation or not invitation.is_active:
            raise HTTPException(
                status_code=401,
                detail="Invitation not found or not active")
        return TokenVerificationResponse(
            message="Token is valid",
            email=email,
            roles=roles,
            full_name=full_name,
            company_id=company_id
        )
    except TokenExpiredError as e:
        return JSONResponse(status_code=401, content={"message": str(e)})
    except CustomInvalidTokenError as e:
        return JSONResponse(status_code=401, content={"message": str(e)})


# endpoint for complete registration with token and password
@router.post("/register/complete")
def complete_registration(data: RegistrationCompletion,
                          background_tasks: BackgroundTasks,
                          db: Session = Depends(get_db),
                          ):
    """
    Эндпойнт для завершения регистрации пользователя.

    :param data: Схема для завершения регистрации пользователя
    :param background_tasks: BackgroundTasks
    :param db: Сессия базы данных
    :return: Сообщение об успешном завершении регистрации

    1. Проверяем токен регистрации, при успешной проверке получаем из него email и роли
    2. Проверяем наличие пользователя с таким же email в БД
    2. Хэшируем новый пароль
    3. Создаем нового пользователя с привязкой к компании
    4. Отправляем письмо об успешной регистрации
    5. Возвращаем 201 код и сообщение об успешном создании пользователя

    Пример схемы для завершения регистрации пользователя
    {
    "token": "{token}",
    "password": "{password}",
    "company_id": "1",
    "full_name": "Петрова Анна Юрьевна"
    }
    """
    try:
        email, roles, full_name, company_id = verify_registration_token(data.token)
        # if crud_user.get_by_email(db, email=email):
        #     raise HTTPException(
        #         status_code=409,
        #         detail="The user with this username already exists in the system.",
        #     )
        if not roles:
            raise HTTPException(
                status_code=401,
                detail="No email or roles provided")
        # hash new password
        hashed_password = get_password_hash(data.password)
        # create new user
        user_in = DBUser(full_name=full_name,
                         email=email,
                         hashed_password=hashed_password,
                         is_active=True,
                         roles=roles,
                         company_id=data.company_id)
        db.add(user_in)
        db.commit()
        # delete invitation record
        # delete_invitation(db, email=email)
        # change invitation status
        change_invitation_status(db, email=email)
        # send email about successful registration in background
        background_tasks.add_task(send_new_account_complete_registration_email,
                                  email_to=user_in.email,
                                  email=user_in.email,
                                  full_name=user_in.full_name)
        logger.info(
            event_type="User registration",
            obj=f"{user_in.full_name}",
            subj="",
            action="User created successfully",
            additional_info=f"{user_in.email}"
        )
        return JSONResponse(status_code=201, content={"message": "User created successfully"})
    except TokenExpiredError as e:
        return JSONResponse(status_code=401, content={"message": str(e)})
    except CustomInvalidTokenError as e:
        return JSONResponse(status_code=401, content={"message": str(e)})


@router.post("", response_model=User, status_code=201, deprecated=True)
def create_user(
        *,
        db: Session = Depends(get_db),
        user_in: UserCreate,
        current_user: User = Depends(lambda: get_current_user_with_roles([UserRole.SUPERADMIN, UserRole.ADMIN])),
):
    """
    Простой эндпойнт для создания пользователя.


    :param db: Сессия базы данных
    :param user_in: Данные для создания пользователя
    :param current_user: Текущий пользователь с ролью SUPERADMIN и ADMIN
    :return: Созданный пользователь

    1. Проверяем, существует ли пользователь с таким же email
    2. Если пользователь существует, то возвращаем ошибку
    3. Если пользователь не существует, то создаем его
    4. Если включена отправка email, то отправляем письмо с данными для входа в систему
    """
    logger.error(f'Current USER: {current_user}')
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=409,
            detail="The user with this username already exists in the system.",
        )
    user = crud_user.create(db, obj_in=user_in)
    if config.EMAILS_ENABLED and user_in.email:
        send_new_account_email(email_to=user_in.email, email=user_in.email, password=user_in.password)
    return JSONResponse(status_code=201, content={"message": "User created successfully"})


@router.put("/{user_id}", response_model=User)
def update_user(
        user_id: int,
        *,
        request: Request,
        db: Session = Depends(get_db),
        user_in: UpdateUserProfile,
        background_tasks: BackgroundTasks,
        current_user: DBUser = Depends(get_current_active_user),
):
    """
    Эндпойнт для обновления конкретного пользователя по id.

    :param user_id: ID пользователя -  для обновления пользователя по id
    :param request:
    :param db: Сессия базы данных
    :param user_in: Данные для обновления пользователя
    :param background_tasks:
    :param current_user: Текущий пользователь со статусом активный
    :return: Обновленный пользователь

    Схема для обновления данных
    {
    "email": "{email}",
    "is_active": True,
    "full_name": "{Some full name}",
    "roles": [UserRole.USER, UserRole.ADMIN],
    "password": "0000"
    }
    """

    # restrict access for superadmin and admin
    # get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])

    user_to_update = crud_user.get_or_404(db, user_id=user_id, current_user=current_user)

    try:
        crud_user.update(
            db,
            current_user=current_user,
            db_obj=user_to_update,
            update_data=user_in,
            background_tasks=background_tasks
        )
        return JSONResponse(status_code=201, content={"message": "User updated successfully"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})


@router.put("/profile", response_model=User)
def update_user_profile(
        *,
        request: Request,
        db: Session = Depends(get_db),
        user_in: UpdateUserProfile,
        background_tasks: BackgroundTasks,
        current_user: DBUser = Depends(get_current_active_user)):

    """
    Эндпойнт для обновления данных профиля пользователя


    :param request:
    :param db:
    :param user_in:
    :param background_tasks:
    :param current_user:
    :return: Обновленный пользователь
    """

    try:
        crud_user.profile_update(
            db_session=db,
            user_id=current_user.id,
            current_user=current_user,
            update_data=user_in,
            background_tasks=background_tasks,
        )
        return JSONResponse(status_code=201, content={"message": "User Profile updated successfully"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})


@router.get("/me", response_model=User)
def read_user_me(
        db: Session = Depends(get_db),
        current_user: DBUser = Depends(get_current_active_user),
):
    """
    Эндпойнт для получения данных текущего активного пользователя

    :param db Сессия базы данных
    :param current_user Текущий пользователь со статусом активный
    :return возвращаем текущего пользователя
    """
    return current_user


@router.get("/{user_id}", response_model=User)
def read_user_by_id(user_id: int,
                    current_user: User = Depends(get_current_active_user),
                    db: Session = Depends(get_db)):
    """
    Эндпойнт для получения пользователя по user_id
    :param user_id пользователя
    :param current_user Текущий пользователь со статусом активный
    :param db Сессия базы данных
    :return возвращаем текущего пользователя

    1. Проверяем роль пользователя  - только админ и суперадмин
    2. Получаем пользователя по id
    """
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])
    user = crud_user.get_or_404(db, user_id=user_id, current_user=current_user)
    return user


# @router.put("/{user_id}", response_model=User)
# def update_user(*, db: Session = Depends(get_db), user_id: int, user_in: UserUpdate,
#                 current_user: DBUser = Depends(get_current_active_user),
#                 ):
#     """
#     Эндпойнт для обновления данных пользователя
#     :param db Сессия базы данных
#     :param user_id ID пользователя
#     :param user_in Схема для обновления пользователя
#     :param current_user текущий пользователя с правами суперадмин
#     :return возвращаем обновленного пользователя
#     """
#     crud_user.update(db, current_user=current_user, db_obj=current_user, update_data=user_in)
#     return JSONResponse(status_code=201, content={"message": "User updated successfully"})


# endpoint for deleting user
@router.delete("/{user_id}", response_model=Message)
def delete_user(*, db: Session = Depends(get_db), user_id: int,
                current_user: User = Depends(get_current_active_user),
                ):
    """Эндпойнт для удаления пользователя


    :param db Сессия базы данных
    :param user_id ID пользователя
    :param current_user текущий пользователя с правами суперадмин
    :return message:  - message about deleting"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    try:
        crud_user.remove(db_session=db, id=user_id)
        return {"message": "User was deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error while deleting user {e}")


# endpoint for uploading user avatar
@router.post("/upload_avatar/{user_id}", response_model=AvatarUpload)
def upload_avatar(user_id: int,
                  db: Session = Depends(get_db),
                  file: UploadFile = File(...),
                  current_user: User = Depends(get_current_active_user)
                  ):
    try:
        file_name = crud_user.upload_user_avatar(db_session=db,
                                                      file=file,
                                                      user_id=user_id,
                                                      current_user=current_user)
        return {
            "message": "Avatar uploaded successfully",
            "path_to_avatar": f"{settings.SERVER_HOST}/media/{user_id}/{str(file_name)}"}
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "message": e.detail,
            }
        )







