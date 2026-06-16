from sqlalchemy import ForeignKey, UniqueConstraint
from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import DataBase

class Course(DataBase):
    __tablename__ = 'course'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    display_name: Mapped[str | None] = mapped_column()
    cid: Mapped[str] = mapped_column()

    announcements: Mapped[List["Announcement"]] = relationship(back_populates="course") # noqa
    files: Mapped[List["File"]] = relationship(back_populates="course") # noqa

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="courses") # noqa

    # make some combinations of attributes unique
    __table_args__ = (
        UniqueConstraint("user_id", "cid"),
        UniqueConstraint("user_id", "name"),
        UniqueConstraint("user_id", "display_name")
    )

    @property
    def effective_name(self) -> str:
        return self.display_name or self.name
