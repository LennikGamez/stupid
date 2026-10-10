from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from database import DataBase
from semesters import Semester


class User(DataBase):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    stud_id: Mapped[str | None] = mapped_column()

    username: Mapped[str] = mapped_column()
    base_url: Mapped[str] = mapped_column()
    sync_dir: Mapped[str] = mapped_column(unique=True)

    is_favorite: Mapped[bool | None] = mapped_column(default=False)
    # this is just an integer - otherwise there are foreignkey cycles between "semester" and "user"
    favorite_semester_id: Mapped[int | None] = mapped_column()

    courses: Mapped[List["Course"]] = relationship(back_populates="user") # noqa
    semesters: Mapped[List["Semester"]] = relationship(back_populates="user") # noqa
