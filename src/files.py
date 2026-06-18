from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from courses import Course
from database import DataBase
from datetime import datetime
from os import path

class File(DataBase):
    __tablename__ = 'file'

    id: Mapped[int] = mapped_column(primary_key=True)
    stud_id: Mapped[str] = mapped_column()

    name: Mapped[str] = mapped_column()
    subdir: Mapped[str] = mapped_column()

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    course: Mapped["Course"] = relationship(back_populates="files") # noqa

    chdate: Mapped[datetime] = mapped_column(default=datetime.now())

    download_url: Mapped[str | None] = mapped_column()

    # make some combinations of attributes unique
    __table_args__ = (
        UniqueConstraint("course_id", "stud_id"),
    )

    @property
    def file_dir(self):
        return path.abspath(path.join(self.course.user.sync_dir, self.course.effective_name, self.subdir))

    @property
    def file_path(self):
        return path.join(str(self.file_dir), self.name)
