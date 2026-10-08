from argparse import ArgumentParser, Namespace
from getpass import getpass
from logging import getLogger
from os import path, pardir, makedirs
from urllib.parse import urlparse

import keyring
from sqlalchemy import Engine
from sqlalchemy.orm import Session as dbSession

from api_navigator import ApiNavigator
from courses import Course
from users import User
from web_session_manager import WebSessionManager

logger = getLogger(__name__)

class CLI:
    def __init__(self, engine: Engine, cmd: Namespace):
        # database engine as attribute
        self.engine: Engine = engine
        self.cmd: Namespace = cmd
    @staticmethod
    def parse_args() -> Namespace:
        """this static method parses the given command line arguments and returns a corresponding Namespace object"""
        # main arg parser
        parser = ArgumentParser()
        # flag for an gui mode in the future
        parser.add_argument("--gui", action="store_true")
        subparsers = parser.add_subparsers(dest="cmd")

        # user parser
        parser_user = subparsers.add_parser("users", help="Get user info")
        parser_user.add_argument("user_cmd", choices=["list", "add", "remove", "change_password", "check_login"])
        parser_user.add_argument("--username", "-u", help="Username")

        # file parser
        parser_files = subparsers.add_parser("files", help="Get file info")
        parser_files.add_argument("file_cmd", choices=[None, "sync"], help="choose what to do with files")
        parser_files.add_argument("--username", "-u", help="Username")

        # course parser
        parser_course = subparsers.add_parser("courses", help="Manage your courses")
        parser_course.add_argument("course_cmd", choices=["sync", "list"])
        parser_course.add_argument("--username", "-u", help="username")

        return parser.parse_args()

    def get_user(self):

        with dbSession(self.engine) as session:
            if self.cmd.username:
                user = session.query(User).filter(User.username == self.cmd.username).first()
            else:
                logger.info("no user specified - trying to get favorite (first) user")
                user = session.query(User).first()
                logger.info("got user: " + str(user.username))

        if not user:
            logger.error("User not found")
            exit(1)

        return user

    def run_cli(self):
        cmd = self.cmd
        if cmd.cmd == "users":
            if cmd.user_cmd == "list":
                with dbSession(self.engine) as session:
                    users = session.query(User).all()

                for u in users:
                    print(u.username)

            elif cmd.user_cmd == "add":
                url = input("Enter url to studip instance (e.g. 'https://studip.example.com'): ")
                url_parsed = urlparse(url)

                # check if valid url was entered
                if not (url_parsed.scheme and url_parsed.netloc):
                    raise ValueError("Invalid url")

                if cmd.username:
                    username = cmd.username
                else:
                    print("Please enter details for adding user")
                    username = input("Username: ")

                password = getpass(f"Enter {username}'s password: ", )  # echo_char="*" for later python =< 3.14

                sync_dir = input(
                    f"Enter directory to sync to if empty defaults to: {path.join(path.expanduser("~"), "PiDuts")}")

                if sync_dir.strip() == "":
                    sync_dir = path.join(path.expanduser("~"), "PiDuts")

                if not path.exists(path.abspath(path.join(sync_dir, pardir))):
                    raise ValueError("Directory does not exist")

                makedirs(sync_dir, exist_ok=True)

                user = User(username=username.strip(), base_url=url, sync_dir=sync_dir)

                with dbSession(self.engine) as session:
                    try:
                        session.add(user)
                        session.commit()
                        session.refresh(user)
                        logger.info(f"Successfully added user {username}")

                        keyring.set_password("pi_duts", str(user.id), password)
                        check_pass = keyring.get_password("pi_duts", str(user.id))
                        if check_pass == password:
                            logger.info("Password set successfully")

                        # login and get stud_id for user
                        with WebSessionManager(user) as wsm:
                            nav = ApiNavigator(wsm, self.engine)
                            user.stud_id = nav.get_user_info_via_session_token()
                        logger.info(user.stud_id)

                        session.commit()
                        session.refresh(user)
                    except Exception as e:
                        session.rollback()
                        logger.error(e)


                #with dbSession(self.engine) as session:
                #    try:
                #        session.commit()
                #        logger.info(f"Successfully updated user {username}")
                #    except Exception as e:
                #        session.rollback()
                #        logger.error(e)


            elif cmd.user_cmd == "change_password":
                if cmd.username:
                    username = cmd.username
                else:
                    username = input("Username: ")
                password = getpass("Password: ", )  # echo_char="*" for later python =< 3.14

                with dbSession(self.engine) as session:
                    user = session.query(User).filter(User.username == username).first()
                    if user:
                        user_id = user.id
                    else:
                        logger.info("user not found!")
                        exit(1)

                keyring.set_password("pi_duts", str(user_id), password)
                check_pass = keyring.get_password("pi_duts", str(user_id))
                if check_pass == password:
                    print("Password changed successfully")

            elif cmd.user_cmd == "remove":
                pass

            elif cmd.user_cmd == "check_login":
                user = self.get_user()

                with WebSessionManager(user) as session:
                    session._show_cookies()
                    # nav = Navigator(self.engine, session, user)


        elif cmd.cmd == "files":
            if cmd.file_cmd == "sync":
                user = self.get_user()

                with WebSessionManager(user) as session:
                    nav = ApiNavigator(session, self.engine)
                    nav.sync_files()


        elif cmd.cmd == "courses":
            if cmd.course_cmd == "list":
                user = self.get_user()

                with dbSession(self.engine) as session:
                    courses = session.query(Course).filter(Course.user_id == user.id).all()
                    for c in courses:
                        print(f"{c.id}: {c.name}")

            if cmd.course_cmd == "sync":
                user = self.get_user()

                with WebSessionManager(user) as session:
                    nav = ApiNavigator(session, self.engine)
                    nav.get_course_list_for_user()


