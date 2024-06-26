from typing import List, Optional, Generic, TypeVar, Type

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base_class import Base
from user.models import User, UserRole

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with defaults methods to Create, Read, Update, Delete (CRUD)
        ** Parameters **
        * model: A SQLAlchemy model class
        * schema: A Pydentic model (schema) class
        """
        self.model = model

    def get(self, db_session: Session, id: int) -> Optional[ModelType]:
        return db_session.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db_session: Session, *, skip=0, limit=100) -> List[ModelType]:
        return db_session.query(self.model).offset(skip).limit(limit).all()

    def create(self, db_session: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db_session.add(db_obj)
        db_session.commit()
        db_session.refresh(db_obj)
        return db_obj

    def update(
            self, db_session: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType
               ) -> ModelType:
        # obj_data = jsonable_encoder(obj_in)
        obj_data = obj_in.model_dump(exclude_unset=True)
        update_data = obj_in.model_dump(exclude_defaults=True)
        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            # if field in update_data:
            #     setattr(db_obj, field, update_data[field])
        db_session.add(db_obj)
        db_session.commit()
        db_session.refresh(db_obj)
        return db_obj

    def remove(self, db_session: Session, *, id: int) -> ModelType:
        obj = db_session.query(self.model).get(id)
        db_session.delete(obj)
        db_session.commit()
        return obj



