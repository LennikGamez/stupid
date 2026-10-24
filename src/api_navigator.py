import logging, json
from sqlalchemy.orm import Session as dbSession
from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert
from os import path, makedirs
from datetime import datetime

from courses import Course
from semesters import Semester
from files import File
from web_session_manager import WebSessionManager
from constants import *

logger = logging.getLogger(__name__)


class ApiNavigator:
    def __init__(self, wsm: WebSessionManager, engine: Engine ):
        self.wsm = wsm
        self.engine = engine

    def fetch_semester_data(self):
        semester_list = self.wsm.get(SEMESTER_LIST).json().get("data")

        semesters = {semester.get("id"): {
            "name": semester.get("attributes").get("title"),
            "start": datetime.fromisoformat(semester.get("attributes").get("start")),
            "end": datetime.fromisoformat(semester.get("attributes").get("end")),
            "stud_id": semester.get("id"),
            "current": semester.get("attributes").get("is-current"),
            "user_id": self.wsm.user.id
        } for semester in semester_list}

        return semesters
        

    def get_user_info_via_session_token(self):
        res = self.wsm.get(USER_INFO)
        json_data = res.json()
        return json_data.get("data").get("id") # stud_id


    def _relate_course_object_and_semester(self, course_obj: dict, semester_id, session: dbSession):
        course_obj["semester_id"] = semester_id

    def _get_semesters_in_db(self, session) -> dict[str, int]:
        # extract all semester stud_ids from the database
        semesters_in_db = session.query(Semester).all()
        return {semester.stud_id: semester.id for semester in semesters_in_db}

    def get_course_list_for_user(self):
        if self.wsm.user.stud_id is None:
            raise Exception("stud ID missing")
        res = self.wsm.get(COURSE_LIST(self.wsm.user.stud_id))
        course_api_data = res.json().get("data")


        with dbSession(self.engine) as session:
            # prepare variable only fetch the actual data if at least one course requires it
            semesters_endpoint_data = {}
            # extract all semester stud_ids from the database
            db_semester_stud_ids_ids = self._get_semesters_in_db(session)
            courses = []
            for course in course_api_data:

                c = {
                    "stud_id": course.get("id"),
                    "name": course.get("attributes").get("title"),
                    "user_id": self.wsm.user.id
                }

                
                start_semester_stud_id = course.get("relationships").get("start-semester").get("data").get("id")
                # check for each course if its start-semester is already in the database
                if start_semester_stud_id in db_semester_stud_ids_ids.keys():
                    # print("Semester is already known", start_semester_stud_id, ": ", db_semester_stud_ids[start_semester_stud_id])
                    self._relate_course_object_and_semester(c, db_semester_stud_ids_ids[start_semester_stud_id], session)
                else:
                    if not semesters_endpoint_data:
                        print("Fetching Semester list...")
                        semesters_endpoint_data = self.fetch_semester_data()

                    if not start_semester_stud_id in semesters_endpoint_data.keys():
                        print("start semester does not exist")
                        return

                    # print("Inserting new Semester into database with stud_id: ", start_semester_stud_id)
                    try:
                        sql_stmt = insert(Semester).values(semesters_endpoint_data[start_semester_stud_id]).on_conflict_do_nothing(
                            index_elements=["stud_id"],
                        ).returning(Semester)
                        session.execute(sql_stmt)
                        session.commit()
                        logger.info(
                            f"Successfully inserted/updated 1 semester"
                        )

                    except Exception as e:
                        session.rollback()
                        logger.error(e)


                    # get updated semester list
                    db_semester_stud_ids_ids = self._get_semesters_in_db(session)
                    self._relate_course_object_and_semester(c, db_semester_stud_ids_ids[start_semester_stud_id], session)

                courses.append(c)
                    
       
            # insert courses
            try:
                sql_stmt = insert(Course).values(courses)
                sql_stmt = sql_stmt.on_conflict_do_update(
                    index_elements=["user_id", "stud_id"],
                    set_=dict(
                        name=sql_stmt.excluded.name,
                        semester_id=sql_stmt.excluded.semester_id,
                    )
                )
                session.execute(sql_stmt)
                session.commit()
                logger.info(
                    f"Successfully inserted/updated {len(courses)} courses"
                )

            except Exception as e:
                session.rollback()
                logger.error(e)
                logger.error(e.args)

        return True

    def _download_file(self, file: File, **kwargs) -> bool:
        if not file.downloaded and not path.exists(file.file_path):
            try:
                if not path.exists(file.file_dir):
                    makedirs(file.file_dir)

                if not "pre_gen_dir_no_file_download" in kwargs.keys() or not kwargs["pre_gen_dir_no_file_download"]:

                    response = self.wsm.get(file.download_url)


                    with open(file.file_path, "wb") as f:
                        f.write(response.content)

                    with dbSession(self.engine) as session:
                        file.downloaded = True
                        session.commit()

                return True

            except Exception as e:
                logger.error(e)

        return False
        
    def _clone_folder(self, course: Course, url: str, root_dir: str, sub_dir: str = "", **kwargs):
        files_data = self.wsm.get(url + "/file-refs").json().get("data")
        folders = self.wsm.get(url + "/folders").json().get("data")

        for folder in folders:
            name = folder.get("attributes").get("name")
            folder_id = folder.get("id")
            self._clone_folder(course, FOLDER_LIST(folder_id), root_dir=str(self.wsm.user.sync_dir), sub_dir=path.join(sub_dir, name), **kwargs)

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
                self._download_file(file, **kwargs)
                print(f"{file.name} has been downloaded!")

    def sync_files_by_course(self, course: Course, **kwargs):
        root_folder_res = self.wsm.get(ROOT_FOLDER_FOLDERS(course.stud_id))
        if root_folder_res.json().get("data") is None:
            print(f"{course.name} has no file system!")
            logger.info(f"{course.name} has no file system!")
            return
        root_folder_id = root_folder_res.json().get("data")[0].get("id")

        self._clone_folder(course, FOLDER_LIST(root_folder_id), root_dir=str(self.wsm.user.sync_dir), **kwargs)

    def sync_files(self, **kwargs):
        # get relevant courses
        with dbSession(self.engine) as session:
            courses = session.query(Course).filter(Course.user_id == self.wsm.user.id).all()

        # sync every course
        for course in courses:
            self.sync_files_by_course(course, **kwargs)
