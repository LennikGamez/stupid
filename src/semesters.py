from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import DataBase

class Semester(DataBase):
    __tablename__ = 'semester'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    stud_id: Mapped[str] = mapped_column(unique=True)

    current: Mapped[bool] = mapped_column()
    start: Mapped[datetime] = mapped_column()
    end: Mapped[datetime] = mapped_column()

    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    user: Mapped["User"] = relationship(back_populates="semesters") # noqa