import logging
from humps import camelize
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple, Union

import emails
import jwt
from emails.template import JinjaTemplate
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

from core import config
from core.exceptions import TokenExpiredError, CustomInvalidTokenError
from user.models import UserRole
from api.utils.logger import PollLogger
from core.local_config import settings


# Logging
logger = PollLogger(__name__)

password_reset_jwt_subject = "present"


def send_email(email_to: str, subject_template="", html_template="", enviroment={}):

    """
    Базовая функция для отправки писем


    :param email_to: адрес электронной почты куда отправляется письмо
    :param subject_template: тема письма
    :param html_template: шаблон письма
    :param enviroment: словарь с переменными для шаблона
    """

    assert config.EMAILS_ENABLED, "no provided configuration for email variables"
    message = emails.Message(
        subject=JinjaTemplate(subject_template),
        html=JinjaTemplate(html_template),
        mail_from=(config.EMAILS_FROM_NAME, config.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": config.SMTP_HOST, "port": config.SMTP_PORT}

    if config.SMTP_TLS:
        smtp_options["tls"] = True
    if config.SMTP_USER:
        smtp_options["user"] = config.SMTP_USER
    if config.SMTP_PASSWORD:
        smtp_options["password"] = config.SMTP_PASSWORD
    try:
        response = message.send(to=email_to, render=enviroment, smtp=smtp_options)
        logging.info(f"send email to "
                     f"{email_to} with response {response}")
    except Exception as e:
        logging.error(f"Failed to send email to {email_to} with error: {e}")


def send_test_email(email_to: str):
    project_name = config.PROJECT_NAME
    subject = f"{project_name} - Test email"
    with open(Path(config.EMAIL_TEMPLATES_DIR) / "test_email.html") as f:
        template_str = f.read()
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        enviroment={"project_name": config.PROJECT_NAME, "email": email_to},
    )


def send_reset_password_email(email_to: str, email: str, token: str, front_url: str):
    project_name = config.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    with open(Path(config.EMAIL_TEMPLATES_DIR) / "reset_password.html") as f:
        template_str = f.read()
    if hasattr(token, "decode"):
        use_token = token.decode()
    else:
        use_token = token
    server_host = settings.SERVER_HOST
    link = f"{front_url}/reset-password?token={use_token}"
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        enviroment={
            "project_name": config.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": config.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )


# send new account email
def send_new_account_email(email_to: str, full_name: str, email: str, link: str, token: str):
    """
    Отправка письма с ссылкой для завершения регистрации

    :param email_to: адрес электронной почты куда отправляется письмо
    :param full_name: полное имя пользователя
    :param email: адрес электронной почты пользователя - здесь это как имя пользователя
    :param link: ссылка на фронтенд
    :param token: токен регистрации
    :return: отправка письма
    """

    project_name = config.PROJECT_NAME
    #logger.info('Income token: ' + str(token))
    subject = f"{project_name} - Завершите регистрацию для {email}"
    with open(Path(config.EMAIL_TEMPLATES_DIR) / "new_account.html") as f:
        template_str = f.read()
    if hasattr(token, "decode"):
        use_token = token.decode()
    else:
        use_token = token
    #logger.info('Use token: ' + str(use_token))
    link = f"{link}?token={use_token}"
    # logger.info(f"Link:  + {str(link)}")
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        enviroment={
            "project_name": config.PROJECT_NAME,
            "email": email_to,
            "full_name": full_name,
            "link": link,
        },
    )


# send email about update profile
def send_update_profile_email(
        email_to: str,
        email: str,
        full_name: str,
        email_changed: bool,
        password_changed: bool,
        both_changed: bool,
        roles_changed: bool,
        role: list
    ):
    """
    Отправка письма с уведомлением об обновлении профиля

    :param email_to: адрес электронной почты куда отправляется письмо
    :param email: адрес электронной почты пользователя - здесь это как имя пользователя
    :param full_name: полное имя пользователя
    :return: отправка письма
    """


    project_name = config.PROJECT_NAME
    subject = f"{project_name} - Профиль обновлен для {email}"
    with open(Path(config.EMAIL_TEMPLATES_DIR) / "update_profile.html") as f:
        template_str = f.read()

    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        enviroment={
            "project_name": config.PROJECT_NAME,
            "email": email_to,
            "full_name": full_name,
            "email_changed": email_changed,
            "password_changed": password_changed,
            "both_changed": both_changed,
            "role_changed": role_changed,
            "role": role
        },
    )


# send new account complete registration email
def send_new_account_complete_registration_email(email_to: str, email: str, full_name: str):
    """
    Отправка письма с подтверждением завершения регистрации

    :param email_to: адрес электронной почты куда отправляется письмо
    :param email: адрес электронной почты пользователя - здесь это как имя пользователя
    :param full_name: полное имя пользователя
    :return: отправка письма"""

    project_name = config.PROJECT_NAME
    subject = f"{project_name} - Регистрация завершена для {email}"
    with open(Path(config.EMAIL_TEMPLATES_DIR) / "new_account_complete_registration.html") as f:
        template_str = f.read()
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        enviroment={
            "project_name": config.PROJECT_NAME,
            "email": email_to,
            "full_name": full_name,
        },
    )


# generate registration token
def generate_registration_token(email: str, roles: List[UserRole], full_name: str, company_id: int) -> str:
    """
    Генерация токена при регистрации пользователя

    :param email: email пользователя
    :param roles: список ролей пользователя
    :param full_name: Полное имя пользователя
    :param company_id: id  компании
    :return: токен
    """
    data = {
        "sub": email,
        "roles": roles,
        "full_name": full_name,
        "company_id": company_id,
        "exp": datetime.utcnow() + timedelta(hours=config.EMAIL_REGISTER_TOKEN_EXPIRE_HOURS),
        # "exp": datetime.utcnow() + timedelta(minutes=1), # expiration time for testing

    }
    encoded_jwt = jwt.encode(data, config.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


# verify registration token
def verify_registration_token(token: str) -> Tuple[str, List[str], str, str]:
    """
    Проверка токена регистрации на валидность

    :param token: токен
    :return: email, roles, admin_email
    """
    try:
        decoded_token = jwt.decode(token, config.SECRET_KEY, algorithm="HS256")
        email = decoded_token["sub"]
        roles = decoded_token["roles"]
        full_name = decoded_token["full_name"]
        company_id = decoded_token["company_id"]
        return email, roles, full_name, company_id
    except jwt.ExpiredSignatureError:
        # decoded_token = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
        # admin_email = decoded_token.get("sub", "Unknown admin")
        raise TokenExpiredError("Token expired. Please request a new one")
    except jwt.InvalidTokenError:
        raise CustomInvalidTokenError("Invalid token")


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Проверка токена сброса пароля на валидность

    :param token: токен
    :return: email
    """
    try:
        decoded_token = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        assert decoded_token["sub"] == password_reset_jwt_subject
        return decoded_token["email"]
    except InvalidTokenError:
        return None


def generate_password_reset_token(email: str):
    """
    Генерация токена сброса пароля

    :param email: email пользователя
    :return: токен
    """
    delta = timedelta(hours=config.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": password_reset_jwt_subject, "email": email},
        config.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def to_camel(string):
    return camelize(string)


class CamelModelMixin(BaseModel):
    class Config:
        alias_generator = to_camel
        populate_by_name = True




