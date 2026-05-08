from json import loads
from bs4 import BeautifulSoup
from navigator import Navigator


COURSE_OVERVIEW_PAGE = "/dispatch.php/my_courses"


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
