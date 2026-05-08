from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class DataBase(DeclarativeBase):
    pass

class User(DataBase):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column()
    base_url: Mapped[str] = mapped_column()
    sync_dir: Mapped[str] = mapped_column()

class Course(DataBase):
    __tablename__ = 'course'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    display_name: Mapped[str] = mapped_column()
    cid: Mapped[str] = mapped_column()

    announcements: Mapped[List["Announcement"]] = relationship(back_populates="course")
    files: Mapped[List["File"]] = relationship(back_populates="course")


class Announcement(DataBase):
    __tablename__ = 'announcement'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    content: Mapped[str] = mapped_column()

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    course: Mapped["Course"] = relationship(back_populates="announcements")


class File(DataBase):
    __tablename__ = 'file'

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column()

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    course: Mapped["Course"] = relationship(back_populates="files")

