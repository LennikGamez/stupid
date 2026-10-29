from pathvalidate import sanitize_filename
from collections import defaultdict
from argparse import ArgumentParser, Namespace
from getpass import getpass
from logging import getLogger
from os import path, pardir, makedirs, getcwd
from urllib.parse import urlparse

import keyring
from sqlalchemy import Engine, update, asc
from sqlalchemy.orm import Session as dbSession
from tabulate import tabulate

from api_navigator import ApiNavigator
from courses import Course
from semesters import Semester
from users import User
from web_session_manager import WebSessionManager

logger = getLogger(__name__)

def print_course_select(all_courses):
        
        # group the courses by semester start
        grouped = defaultdict(list)
        for course in all_courses:
            grouped[course.semester.start].append(course)

        rows = []
        for _semester_start, courses in sorted(grouped.items(), key = lambda g: g[0]): # sort by semester start
            for course in courses:
                rows.append([course.id, course.effective_name])
            rows.append(["", ""])

        print(tabulate(
            rows,
            headers=["ID", "Name",],
            tablefmt="rst"
        ))


class CLI:
    def __init__(self, engine: Engine, cmd: Namespace) -> None:
        # database engine as attribute
        self.engine: Engine = engine
        self.cmd: Namespace = cmd
    @staticmethod
    def parse_args() -> Namespace:
        """this static method parses the given command line arguments and returns a corresponding Namespace object"""
        # main arg parser
        parser = ArgumentParser()
        # flag for a gui mode in the future
        parser.add_argument("--gui", action="store_true")
        parser.add_argument("--username", "-u", help="Username")
        subparsers = parser.add_subparsers(dest="cmd")

        # user parser
        parser_user = subparsers.add_parser("users", help="Get user info")
        parser_user.add_argument("user_cmd", choices=["list", "add", "remove", "change_password", "check_login", "set_favorite"])

        # file parser
        parser_files = subparsers.add_parser("files", help="Get file info")
        parser_files.add_argument("file_cmd", choices=[None, "sync"], help="choose what to do with files")
        parser_files.add_argument("--all-courses", "-a", action="store_true", help="sync all courses")
        parser_files.add_argument("--courses", "-c", help="choose which courses to sync")
        parser_files.add_argument("--all-semesters", "-s", action="store_true", help="if possible select not only your current semester but all semesters")
        parser_files.add_argument("--here", action="store_true", help="try to updating files in current directory")
        parser_files.add_argument("--pre-gen-dirs", action="store_true", help="do not update any files just generate directories")

        # course parser
        parser_course = subparsers.add_parser("courses", help="Manage your courses")
        parser_course.add_argument("course_cmd", choices=["sync", "list"])

        # semester parser
        parser_semesters = subparsers.add_parser("semesters", help="Manage semesters")
        parser_semesters.add_argument("semester_cmd", choices=["sync", "list"])



        return parser.parse_args()

    def get_current_semester(self) -> Semester | None:
        with dbSession(self.engine) as session:
            return session.query(Semester).filter(Semester.current == True).first()

    def get_user(self) -> User:

        with dbSession(self.engine) as session:
            if self.cmd.username:
                user = session.query(User).filter(User.username == self.cmd.username).first()
            else:
                logger.info("no user specified - trying to get favorite user")
                user = session.query(User).filter(User.is_favorite == True).first()
                if user:
                    logger.info("got user: " + str(user.username))
                    return user

                logger.info("no favorite user set - trying to get first user")
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
                url = input("Enter url to stud.ip instance (e.g. 'https://studip.example.com'): ")
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
                    f"Enter directory to sync to if empty defaults to {path.join(path.expanduser("~"), "stupid")}: ")

                if sync_dir.strip() == "":
                    sync_dir = path.join(path.expanduser("~"), "stupid")

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

                        keyring.set_password("stupid", str(user.id), password)
                        check_pass = keyring.get_password("stupid", str(user.id))
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

                keyring.set_password("stupid", str(user_id), password)
                check_pass = keyring.get_password("stupid", str(user_id))
                if check_pass == password:
                    print("Password changed successfully")

            elif cmd.user_cmd == "remove":
                pass

            elif cmd.user_cmd == "check_login":
                user = self.get_user()

                with WebSessionManager(user) as session:
                    session._show_cookies()
                    # nav = Navigator(self.engine, session, user)

            elif cmd.user_cmd == "set_favorite":
                with dbSession(self.engine) as session:
                    all_users = session.query(User).all()
                print(tabulate(
                    [[u.id, u.username, u.base_url, u.is_favorite] for u in all_users],
                    headers=["ID", "Username", "URL", "Favorite"],
                    tablefmt="rst"
                ))
                user_id = int(input("ID of the user you want to favorite: "))

                with dbSession(self.engine) as session:
                    session.execute(
                        update(User),
                        [{"id": u.id, "is_favorite": False} for u in all_users]
                    )
                    session.query(User).filter(User.id == user_id).update({"is_favorite": True})

                    session.commit()


        elif cmd.cmd == "files":
            if cmd.file_cmd == "sync":
                user = self.get_user()
                if cmd.here:
                    sync_dir = user.sync_dir
                    pwd = getcwd()

                    if sync_dir == pwd:
                        print("Syncing all your files...")
                        with WebSessionManager(user) as wsm:
                            nav = ApiNavigator(wsm, self.engine)
                            nav.sync_files()
                        exit()

                    elif not path.commonpath([sync_dir, pwd]) == sync_dir:
                        print("This directory is not inside your stupid folder")
                        exit(1)

                    directories = pwd.removeprefix(sync_dir+path.sep).split(path.sep)
                    directories.reverse()

                    for i in directories:
                        with dbSession(self.engine) as session:
                            user = self.get_user()
                            course = session.query(Course).filter(Course.user_id == user.id).filter(Course.display_name == i or Course.name == i).first()
                            if course:
                                with WebSessionManager(user) as wsm:
                                    nav = ApiNavigator(wsm, self.engine)
                                    nav.sync_files_by_course(course)
                                exit()
                            semesters = session.query(Semester).filter(Semester.user_id == user.id).all()
                            for semester in semesters:
                                if sanitize_filename(semester.name, replacement_text="_") == i:
                                    with WebSessionManager(user) as wsm:
                                        nav = ApiNavigator(wsm, self.engine)
                                        nav.sync_files_by_semester(semester)
                                    exit()

                    print("Could not match this folder: ", pwd)
                    
                else:

                    if cmd.all_courses:
                        with WebSessionManager(user) as session:
                            nav = ApiNavigator(session, self.engine)
                            nav.sync_files(pre_gen_dir_no_file_download=cmd.pre_gen_dirs, sync_all_semesters=cmd.all_semesters)

                    else:
                        if cmd.courses:
                            selected_c_ids = cmd.courses.split(",")
                        else:
                            print("Since you have entered any courses you have to select them manually: ")

                            with dbSession(self.engine) as session:
                                get_all_semesters = cmd.all_semesters

                                current_semester = self.get_current_semester()
                                if not current_semester:
                                    get_all_semesters = True

                                if get_all_semesters:
                                    all_courses = session.query(Course).filter(Course.user_id == user.id).order_by(asc(Course.name)).all()
                                    print("Courses of all Semesters:")
                                else:
                                    print("Courses of your current Semester:")
                                    all_courses = session.query(Course).filter(Course.user_id == user.id).filter(Course.semester_id == current_semester.id).order_by(asc(Course.name)).all()
                                    

                                print_course_select(all_courses)

                            selected_c_ids = input("Select comma separated course IDs to sync e.g. '1,4,7': ").split(",")

                        with dbSession(self.engine) as session:
                            selected_courses = session.query(Course).filter(Course.id.in_(selected_c_ids)).all()

                        with WebSessionManager(user) as session:
                            nav = ApiNavigator(session, self.engine)
                            for c in selected_courses:
                                nav.sync_files_by_course(c, pre_gen_dir_no_file_download=cmd.pre_gen_dirs)







        elif cmd.cmd == "courses":
            if cmd.course_cmd == "list":
                user = self.get_user()

                with dbSession(self.engine) as session:
                    all_courses = session.query(Course).filter(Course.user_id == user.id).order_by(asc(Course.name)).all()
                    print_course_select(all_courses)

            if cmd.course_cmd == "sync":
                user = self.get_user()

                with WebSessionManager(user) as session:
                    nav = ApiNavigator(session, self.engine)
                    nav.get_course_list_for_user()

        elif cmd.cmd == "semesters":
            if cmd.semester_cmd == "list":
                user = self.get_user()
                with dbSession(self.engine) as session:
                    semes = session.query(Semester).filter(Semester.user_id == user.id).all()
                print(tabulate(
                    [[s.id, s.name] for s in semes],
                    headers=["ID", "Name",],
                    tablefmt="rst"
                ))

            elif cmd.semester_cmd == "sync":
                pass


