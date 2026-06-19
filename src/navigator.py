import logging

import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from os import makedirs, path
from datetime import datetime ,timezone

from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from courses import Course
from users import User
from files import File
from web_session_manager import WebSessionManager
from constants import *

logger = logging.getLogger(__name__)

class Navigator:
    def __init__(self, db_engine: Engine, wsm: WebSessionManager, user: type[User]):
        """The Navigator class takes a base_url in the constructor which is just the domain of your University's page"""
        self.engine = db_engine
        self.user = user
        self.wsm = wsm


    def _download_file(self, file: File) -> bool:
        if not file.downloaded and not path.exists(file.file_path):
            try:
                response = self.wsm.get(file.download_url, use_base_url=False)

                if not path.exists(file.file_dir):
                    makedirs(file.file_dir)

                with open(file.file_path, "wb") as f:
                    f.write(response.content)

                with Session(self.engine) as session:
                    file.downloaded = True
                    session.commit()

                return True

            except Exception as e:
                logger.error(e)

        return False

    def _clone_folder(self, course: type[Course], url: str, root_dir:str, sub_dir:str="") -> None:
        response = self.wsm.get(url, use_base_url=False)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(id="files_table_form")
        if not form:
            raise Exception("Invalid URL!")
        data_files = json.loads(str(form.get("data-files")))

        # do DB updates/inserts first, then iterate over updated values. That way files can mark themselves
        # as downloaded or e.g. update their name if the file exists twice
        files = [
            {
                "stud_id": f.get("id"),
                "name": f.get("name"),
                "subdir": sub_dir,
                "course_id": course.id,
                "chdate": datetime.fromtimestamp(f.get("chdate"), tz=timezone.utc),
                "download_url": f.get("download_url"),
            }
            for f in data_files
        ]

        with Session(self.engine) as session:
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


        for file in res_files:
            self._download_file(file)

            print(f"{file.name} has been downloaded!")

        data_folders = json.loads(str(form.get("data-folders")))
        for folder in data_folders:
            self._clone_folder(course, folder.get("url"), root_dir, path.join(sub_dir, folder.get("name")))


    def sync_files(self) -> bool:
        # get relevant courses
        with Session(self.engine) as session:
            courses = session.query(Course).filter(Course.user_id == self.user.id).all()

        # sync every course
        for course in courses:
            url = urljoin(str(self.user.base_url), EP_FILE_DIR_PAGE + course.cid,)
            self._clone_folder(course, url, root_dir=str(self.user.sync_dir))

        return False

    def sync_courses(self) -> bool:
        response = self.wsm.get(EP_COURSES)
        soup = BeautifulSoup(response.content, "html.parser")
        script_tag = soup.find(id="vue-vuex-store-data-mycourses")
        if not script_tag:
            raise Exception("Could not find any course data!")
        raw_data = json.loads(script_tag.get_text())

        courses = [
            {
                "cid": c.id,
                "name": c.name,
                "user_id": self.user.id
                # "number": c.number
            }
            for c in list(raw_data["setCourses"].values())
        ]

        with Session(self.engine) as session:
            try:
                sql_stmt = insert(Course).values(courses)
                sql_stmt.on_conflict_do_nothing(
                    index_elements=["user_id", "cid"],
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


    
