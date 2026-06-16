import logging
import keyring
import requests as req
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from os import makedirs, path

from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from courses import Course
from users import User

# endpoints
EP_LOGIN = "/dispatch.php/login"
EP_START = "/dispatch.php/start/index"
EP_COURSES = "/dispatch.php/my_courses"
EP_MESSAGES_OVERVIEW = "/dispatch.php/messages/overview"
EP_FILE_DIR_PAGE = "/dispatch.php/course/files?cid="
EP_FILE_FLAT_PAGE = "/dispatch.php/course/files/flat?cid="
EP_DOWNLOAD_NEWEST_FILES = "/dispatch.php/course/files/newest_files?cid="

logger = logging.getLogger(__name__)

class Navigator:
    def __init__(self, db_engine: Engine, user: type[User]):
        """The Navigator class takes a base_url in the constructor which is just the domain of your University's page"""
        self.engine = db_engine
        self.user = user
        self.session = req.Session()

    def _get(self, endpoint, use_base_url = True, base_url: str="",) -> req.Response:
        if base_url == "": base_url = self.user.base_url

        return self.session.get(urljoin(base_url, endpoint) if use_base_url else endpoint)

    def _post(self, endpoint, data=None) -> req.Response:
        return self.session.post(urljoin(str(self.user.base_url), endpoint), data)

    def _extract_sec_token_from_loginpage(self) -> tuple[bool, tuple[str, str] | None]:
        res = self._get(EP_LOGIN).content
        bs = BeautifulSoup(res, "html.parser")

        form = bs.find(id="login-form")

        if not form:
            logger.error("Could not find the login-form!")
            return False, ("", "")

        security_token_input = form.find(attrs={"name": "security_token"})
        if not security_token_input:
            logger.error("Security Token was not found!")
            return False, ("", "")
        security_token = security_token_input.get("value")

        login_ticket_input = form.find(attrs={"name": "login_ticket"})
        if not login_ticket_input:
            logger.error("Login Ticket was not found!")
            return False, ("", "")
        login_ticket = login_ticket_input.get("value")

        return True, (str(security_token), str(login_ticket))

    def _download_file(self, dl_url:str, root_dir:str, sub_dir:str, file_name:str) -> bool:
        response = self._get(dl_url, use_base_url=False)
        directory = path.abspath(path.join(root_dir, sub_dir))
        if not path.exists(directory):
            makedirs(directory)

        with open(path.join(directory, file_name), "wb") as f:
            f.write(response.content)

        return True

    def _clone_folder(self, url: str, root_dir:str, sub_dir:str="") -> None:
        response = self._get(url, use_base_url=False)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(id="files_table_form")
        if not form:
            raise Exception("Invalid URL!")
        data_files = json.loads(str(form.get("data-files")))
        data_folders = json.loads(str(form.get("data-folders")))

        for file in data_files:
            # yield file
            self._download_file(file.get("download_url"), root_dir, sub_dir, file.get("name"))
            # here could be a potential DB Update
            print(f"{file.get('name')} has been downloaded!")
        for folder in data_folders:
            # yield {"folder": folder, "files": list(clone_folder(navigator, folder.get("url")))}
            self._clone_folder(folder.get("url"), root_dir, path.join(sub_dir, folder.get("name")))
            # here could be a potential DB Update


    def session_login(self) -> bool:
        tk_success, (tk_sec, tk_login) = self._extract_sec_token_from_loginpage()
        if not tk_success: return False

        res = self._post(EP_LOGIN, data={
             "loginname": self.user.username,
             "password": keyring.get_password("pi_duts", str(self.user.id)),
             "security_token": tk_sec,
             "login_ticket": tk_login,
             "resolution": "",
             "Login": ""
        })


        return True

    def sync_files(self) -> bool:
        # get relevant courses
        with Session(self.engine) as session:
            courses = session.query(Course).filter(Course.user_id == self.user.id).all()

        # sync every course
        for course in courses:
            url = urljoin(str(self.user.base_url), EP_FILE_DIR_PAGE + course.cid,)
            self._clone_folder(url, root_dir=str(self.user.sync_dir))

        return False

    def sync_courses(self) -> bool:
        response = self._get(EP_COURSES)
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


    
