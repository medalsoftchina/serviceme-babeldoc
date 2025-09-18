from sqlalchemy.ext.declarative import declarative_base
from sqlmodel import SQLModel

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Field


class FndModelBase(SQLModel):
    metadata = declarative_base().metadata

class LiteAuditBase(FndModelBase):
    created_by: Optional[str] = Field(nullable=False, default="", description="创建人")
    created_at: Optional[datetime] = Field(
        nullable=False, default_factory=datetime.utcnow, description="创建时间"
    )
    updated_by: Optional[str] = Field(nullable=False, default="", description="更新人")
    updated_at: Optional[datetime] = Field(
        nullable=False, default_factory=datetime.utcnow, description="更新时间"
    )
    deleted_by: Optional[str] = Field(nullable=False, default="", description="删除人")
    deleted_at: Optional[datetime] = Field(
        nullable=False, default=datetime(1900, 1, 1), description="删除时间"
    )
    deleted: bool = Field(default=False, nullable=False, description="是否已经删除")

    @classmethod
    def all_query(cls, session):
        return session.query(cls)

    @classmethod
    def query(cls, session):
        return session.query(cls).filter_by(deleted=False)

    @classmethod
    def count(cls, session):
        return cls.query(session).count()

    @classmethod
    def get(cls, session, _id, raise_404=False):
        instance = cls.query(session).filter_by(deleted=False, id=_id).first()
        if not instance and raise_404:
            raise HTTPException(status_code=404, detail=f"{cls.__name__} not found")

        return instance

    @classmethod
    def delete_one(cls, session, _id, user_id="", raise_404=False):
        instance = cls.get(session, _id, raise_404=raise_404)
        cls.delete(instance, session, user_id)

        return instance

    @classmethod
    def delete(cls, instances, session, user_id=""):
        """逻辑删除，支持单个实例或批量实例"""
        # 如果传入的不是列表，将其转换为列表
        if not isinstance(instances, list):
            instances = [instances]

        current_time = datetime.utcnow()
        for instance in instances:
            instance.deleted = True
            instance.deleted_at = current_time
            instance.deleted_by = user_id
            session.add(instance)

        session.commit()

    @classmethod
    def create(cls, session, create_dict, user_id=""):
        """创建实例"""
        instance = cls(**create_dict)
        instance.created_by = user_id
        instance.created_at = datetime.utcnow()
        session.add(instance)
        session.commit()
        session.refresh(instance)

        return instance

    @classmethod
    def create_without_commit(cls, session, create_dict, user_id=""):
        """创建实例"""
        instance = cls(**create_dict)
        instance.created_by = user_id
        instance.created_at = datetime.utcnow()
        session.add(instance)

        return instance

    @classmethod
    def insert_one(cls, session, obj, user_id=""):
        """创建实例"""
        create_dict = {}
        if not isinstance(obj, dict):
            for key in obj.__fields__:
                if getattr(obj, key) is not None:
                    create_dict[key] = getattr(obj, key)
        else:
            create_dict = obj

        return cls.create(session, create_dict, user_id)

    def update(self, session, update_dict, user_id=""):
        """创建实例"""
        for key, value in update_dict.items():
            if value is not None and key in self.__fields__:
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        self.updated_by = user_id
        session.add(self)
        session.commit()
        session.refresh(self)

        return self

    def hard_delete(self, session):
        """物理删除、硬删除"""
        session.delete(self)
        session.commit()