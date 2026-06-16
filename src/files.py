from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import DataBase
from datetime import datetime

class File(DataBase):
    __tablename__ = 'file'

    id: Mapped[int] = mapped_column(primary_key=True)
    stud_id: Mapped[str] = mapped_column()

    display_name: Mapped[str] = mapped_column()

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    course: Mapped["Course"] = relationship(back_populates="files") # noqa

    chdate: Mapped[datetime] = mapped_column(default=datetime.now())

    # make some combinations of attributes unique
    __table_args__ = (
        UniqueConstraint("course_id", "stud_id"),
    )
