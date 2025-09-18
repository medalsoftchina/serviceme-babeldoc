from datetime import date
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Annotated
from typing import Optional
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel
from pydantic import condecimal
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import Unicode
from sqlalchemy import UniqueConstraint
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import Text
from sqlmodel import UnicodeText
from app.model.base import LiteAuditBase

class AttachmentStorage(LiteAuditBase, table=True):
    __tablename__ = "fnd_biz_attachment_storage"

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, unique=True, description="附件ID"
    )
    file_name: str = Field(
        sa_column=Column(Unicode(255), default="", nullable=False, comment="上传的附件名")
    )
    file_type: str = Field(
        sa_column=Column(Unicode(255), default="", nullable=False, comment="附件类型")
    )
    file_path: str = Field(
        sa_column=Column(Unicode(255), default="", nullable=False, comment="最终保存路径")
    )
    file_size: int = Field(default=0, nullable=False, description="附件大小，单位为Byte")

    md5: str = Field(
        sa_column=Column(Unicode(32), default="", nullable=False, comment="文件md5")
    )

    status: int = Field(
        sa_column=Column(
            Integer(),
            default=0,
            index=False,
            comment="附件状态：上传成功为1,pdf转为html成功为2, pdf成功翻译为3,pdf翻译进行中为4，pdf翻译排队中为5,pdf翻译失败为6",
        )
    )
    extra_info: str = Field(
        sa_column=Column(Text(), default="{}", nullable=False, comment="附件的额外信息JSON")
    )
    error_message: str = Field(
        sa_column=Column(Unicode(255), default="", nullable=False, comment="处理任务报错信息")
    )
    # 当前用于翻译任务，后续可拓展
    progress: str = Field(
        sa_column=Column(Unicode(255), default="", nullable=False, comment="处理进度")
    )