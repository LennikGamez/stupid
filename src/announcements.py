from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import DataBase


class Announcement(DataBase):
    __tablename__ = 'announcement'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    content: Mapped[str] = mapped_column()

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    course: Mapped["Course"] = relationship(back_populates="announcements")


