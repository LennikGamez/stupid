import logging, json
from sqlalchemy.orm import Session as dbSession
from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert

from courses import Course
from web_session_manager import WebSessionManager

logger = logging.getLogger(__name__)

# Endpoints

API_VERSION = "/jsonapi.php/v1"
USER_INFO = API_VERSION + "/users/me"
course_list = API_VERSION + "/users/<user-id>/courses"
class ApiNavigator:
    # Endpoints
    def __init__(self, wsm: WebSessionManager, engine: Engine ):
        self.wsm = wsm
        self.engine = engine

    def get_user_info_via_session_token(self):
        res = self.wsm.get(USER_INFO)
        json_data = res.json()
        return json_data.get("data").get("id") # stud_id

    def get_course_list_for_user(self):
        if self.wsm.user.stud_id is None:
            raise Exception("stud ID missing")
        COURSE_LIST = course_list.replace("<user-id>", self.wsm.user.stud_id)
        res = self.wsm.get(COURSE_LIST)
        json_data = res.json().get("data")


        courses = [
            {
                "stud_id": c.get("id"),
                "name": c.get("attributes").get("title"),
                "user_id": self.wsm.user.id
            }
        for c in json_data]

        
        with dbSession(self.engine) as session:
            try:
                sql_stmt = insert(Course).values(courses).on_conflict_do_nothing(
                    index_elements=["user_id", "stud_id"],
                )
                session.execute(sql_stmt)
                session.commit()
                logger.info(
                    f"Successfully inserted/updated {len(courses)} courses"
                )

            except Exception as e:
                session.rollback()
                logger.error(e)

        return True

