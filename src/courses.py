from sqlalchemy import ForeignKey
from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import DataBase

class Course(DataBase):
    __tablename__ = 'course'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    display_name: Mapped[str] = mapped_column()
    cid: Mapped[str] = mapped_column()

    announcements: Mapped[List["Announcement"]] = relationship(back_populates="course") # noqa
    files: Mapped[List["File"]] = relationship(back_populates="course") # noqa

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="courses") # noqa

"""
def get_list_of_courses(navigator: Navigator):
    response = navigator.get(COURSE_OVERVIEW_PAGE)
    soup = BeautifulSoup(response.content, "html.parser")
    script_tag = soup.find(id="vue-vuex-store-data-mycourses")
    if not script_tag:
        raise Exception("Could not find any course data!")
    raw_data = loads(script_tag.get_text()) 
    for course in list(raw_data["setCourses"].values()):
        id = course.get("id")
        name = course.get("name")
        number = course.get("number")
        yield {"id": id, "name": name, "number": number}
"""