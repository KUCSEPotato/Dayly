from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tag import Tag
from app.schemas.tag import TagCreate
from app.services.transactions import write_transaction


class TagService:
    def __init__(self, session: Session):
        self.session = session

    def list(self, query: str = "") -> list[Tag]:
        statement = select(Tag)
        if query.strip():
            statement = statement.where(Tag.normalized_name.contains(query.strip().casefold(), autoescape=True))
        return list(self.session.scalars(statement.order_by(Tag.id)))

    def create(self, data: TagCreate) -> Tag:
        with write_transaction(self.session):
            normalized = data.name.casefold()
            tag = self.session.scalar(select(Tag).where(Tag.normalized_name == normalized))
            if tag is None:
                tag = Tag(name=data.name, normalized_name=normalized, color=data.color)
                self.session.add(tag)
                self.session.flush()
            # Reuse the original name/color when a normalized name already exists.
        return tag
