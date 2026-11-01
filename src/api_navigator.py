import logging, json
from typing import Generator
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
        
    def _clone_folder(self, course: Course, all_folders_flat, root_dir: str, **kwargs):
        folders = [{
            "id": f.get("id"),
            "name": f.get("attributes").get("name"),
            "file-url": f.get("relationships").get("file-refs").get("links").get("related"),
            "folder-count": f.get("relationships").get("folders").get("meta").get("count"),
            "file-count": f.get("relationships").get("file-refs").get("meta").get("count")
            
        } for f in all_folders_flat[1::]]

        def get_folderids_and_subdirectory_paths(folders):
            index = 0
            folder_id_subdir = {}

            def read_folder(sub_dir_path="", level=0):
                nonlocal index
                if not index < len(folders):
                    logger.error("not all folders were fetched (page limit too small)")
                    return
                folder = folders[index]
                index += 1
                sub_dir_path = path.join(sub_dir_path, folder["name"])
                if folder["file-count"] > 0:
                    folder_id_subdir.update({
                                                folder["id"]: sub_dir_path
                                            })
                for _ in range(folder["folder-count"]):
                    read_folder(sub_dir_path, level+1)

            while index < len(folders):
                read_folder()
            folder_id_subdir.update({all_folders_flat[0]["id"]: ""}) # add root folder so that files inside root can be matched
            return folder_id_subdir

        folder_list = get_folderids_and_subdirectory_paths(folders)

        # fetch all files in the course and map them to folders in folder_list
        course_files_flat = self.wsm.get(FILE_REFS_FLAT(course.stud_id, 1000000)).json().get("data")
        files = [
            {
                "stud_id": f.get("id"),
                "name": f.get("attributes").get("name"),
                "subdir": folder_list[f.get("relationships").get("parent").get("data").get("id")], # match subdir with prev generated folder_list
                "course_id": course.id,
                "chdate": datetime.fromisoformat(f.get("attributes").get("chdate")),
                "download_url": f.get("meta").get("download-url"),
            }
            for f in course_files_flat
        ]

        # do DB updates/inserts first, then iterate over updated values. That way files can mark themselves
        # as downloaded or e.g. update their name if the file exists twice

        if len(files) < 1:
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


            # group files and subdirectories
            grouped = {}
            for f in res_files:
                if not f.subdir in grouped:
                    grouped[f.subdir] = []
                grouped[f.subdir] += [f]

            for subdir, files in grouped.items():
                level = get_path_level(subdir)
                downloaded_any = True
                for file in files:
                    downloaded = self._download_file(file, **kwargs)
                    if downloaded:
                        if downloaded_any:
                            # print subdir once
                            if subdir:
                                print_indent(subdir, level)
                                level += 1
                            downloaded_any = False
                        print_indent(f"{file.name} has been downloaded!", level)


    def sync_files_by_course(self, course: Course, **kwargs):
        root_folder_res = self.wsm.get(ROOT_FOLDER_FOLDERS(course.stud_id, 1000000))
        root_json = root_folder_res.json()
        if root_json.get("data") is None:
            print(f"> {course.name} has no file system!")
            logger.info(f"{course.name} has no file system!")
            return
        elif root_json.get("data")[0].get("attributes").get("is-empty"):
            print(f"> skipping course {course.effective_name} since it's empty")
            return
        root_folder_id = root_folder_res.json().get("data")[0].get("id")

        print("\n", course.effective_name)
        self._clone_folder(course, root_json.get("data"), root_dir=str(self.wsm.user.sync_dir), **kwargs)

    def sync_files_by_semester(self, semester: Semester, **kwargs):
        with dbSession(self.engine) as session:
            courses_in_semester = session.query(Course).filter(Course.user_id == self.wsm.user.id).filter(Course.semester_id == semester.id).all()
            for course in courses_in_semester:
                self.sync_files_by_course(course, **kwargs)

    def sync_files(self, **kwargs):
        # get relevant courses
        sync_all_semesters = kwargs.get("sync_all_semesters", True)
            
        with dbSession(self.engine) as session:
            if sync_all_semesters:
                print("Syncing all Semesters...")
                courses = session.query(Course).filter(Course.user_id == self.wsm.user.id).all()
            else:
                print("Syncing only current Semester")
                current_semester_res = session.query(Semester).filter(Semester.current == True).first()
                if not current_semester_res:
                    raise Exception("No current Semester was found!")

                current_semester = current_semester_res
                courses = session.query(Course).filter(Course.user_id == self.wsm.user.id).filter(Course.semester_id == current_semester.id).all()
                

        # sync every course
        for course in courses:
            self.sync_files_by_course(course, **kwargs)
