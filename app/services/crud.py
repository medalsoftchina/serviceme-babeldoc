from app.model.attachment_storage.attachment_storage import AttachmentStorage
from sqlmodel import Session
from uuid import UUID

from app.model.common.model import PaginationParams
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import desc

def get_by_attachment_id(db: Session, attachment_id: UUID) -> AttachmentStorage:
    """
    根据文件的id返回文件的某些信息
    """
    audio = (
        AttachmentStorage.query(db)
        .filter(AttachmentStorage.id == attachment_id)
        .first()
    )
    return audio


def get_translate_files(
    db: Session, user_id: str, page_params: PaginationParams
) -> AttachmentStorage:
    """
    根据某个用户的所有翻译文件
    """
    files = AttachmentStorage.query(db).filter(
        AttachmentStorage.created_by == user_id,
        cast(AttachmentStorage.extra_info, JSONB)['type'].astext == 'translate'
    )
    total = files.count()
    files = (
        files.order_by(desc(AttachmentStorage.created_at))
        .offset(page_params.skip)
        .limit(page_params.page_size)
        .all()
    )
    return files, total
