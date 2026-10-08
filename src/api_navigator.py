import logging, json
from sqlalchemy.orm import Session as dbSession
from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert
from os import path, makedirs
from datetime import datetime ,timezone
from urllib.parse import urljoin

from courses import Course
from files import File
from web_session_manager import WebSessionManager

logger = logging.getLogger(__name__)

# Endpoints

API_VERSION = "/jsonapi.php/v1"
USER_INFO = API_VERSION + "/users/me"
COURSE_LIST = lambda user_id: urljoin(API_VERSION, f"/users/{user_id}/courses")
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
        res = self.wsm.get(COURSE_LIST(self.wsm.user.stud_id))
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

    def _download_file(self, file: File) -> bool:
        if not file.downloaded and not path.exists(file.file_path):
            try:
                response = self.wsm.get(file.download_url)

                if not path.exists(file.file_dir):
                    makedirs(file.file_dir)

                with open(file.file_path, "wb") as f:
                    f.write(response.content)

                with dbSession(self.engine) as session:
                    file.downloaded = True
                    session.commit()

                return True

            except Exception as e:
                logger.error(e)

        return False
        
    def _clone_folder(self, course: Course, url: str, root_dir: str, sub_dir: str = ""):
        files_data = self.wsm.get(url + "/file-refs").json().get("data")
        folders = self.wsm.get(url + "/folders").json().get("data")

        for folder in folders:
            name = folder.get("attributes").get("name")
            folder_id = folder.get("id")
            self._clone_folder(course, f"/jsonapi.php/v1/folders/{folder_id}", root_dir=str(self.wsm.user.sync_dir), sub_dir=path.join(sub_dir, name))

        # do DB updates/inserts first, then iterate over updated values. That way files can mark themselves
        # as downloaded or e.g. update their name if the file exists twice
        files = [
            {
                "stud_id": f.get("id"),
                "name": f.get("attributes").get("name"),
                "subdir": sub_dir,
                "course_id": course.id,
                "chdate": datetime.fromisoformat(f.get("attributes").get("chdate")),
                "download_url": f.get("meta").get("download-url"),
            }
            for f in files_data
        ]

        if len(files) < 1:
            print("no files in folder: ", path.join(course.name, sub_dir))
            return
        with dbSession(self.engine) as session:
            try:
                sql_stmt = insert(File)
                sql_stmt = (
                    sql_stmt
                    .values(files)
                    .on_conflict_do_update(
                        index_elements=["course_id", "stud_id"],
                        set_={
                            "name": sql_stmt.excluded.name,
                            "subdir": sql_stmt.excluded.subdir,
                            "chdate": sql_stmt.excluded.chdate,
                            "download_url": sql_stmt.excluded.download_url,
                        }
                    )
                    .returning(File)
                )

                res = session.execute(sql_stmt)

                res_files = res.scalars().all()

                session.commit()

            except Exception as e:
                session.rollback()
                logger.error(e)
                raise Exception("File insertion failed!", e)


            for file in res_files:
                self._download_file(file)
                print(f"{file.name} has been downloaded!")
            

    def sync_files(self):
        # get relevant courses
        with dbSession(self.engine) as session:
            courses = session.query(Course).filter(Course.user_id == self.wsm.user.id).all()

        # sync every course
        for course in courses:
            root_folder_res = self.wsm.get(f"{API_VERSION}/courses/{course.stud_id}/folders")
            if root_folder_res.json().get("data") is None:
                print(f"{course.name} has no file system!")
                continue
            root_folder_id = root_folder_res.json().get("data")[0].get("id")

            self._clone_folder(course, f"/jsonapi.php/v1/folders/{root_folder_id}", root_dir=str(self.wsm.user.sync_dir), )
