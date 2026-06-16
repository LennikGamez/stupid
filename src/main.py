import os.path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session
from urllib.parse import urlparse
from users import User
from navigator import Navigator
from argparse import ArgumentParser
from os import makedirs, environ as env
from appdirs import user_data_dir, user_state_dir
from sqlalchemy import create_engine, text, Engine
from os import path, getcwd, pardir
from getpass import getpass
import keyring
import logging

logger = logging.getLogger(__name__)

class PiDuts:
    def __init__(self):
        # database engine as attribute
        self.engine: Engine

    @staticmethod
    def get_db_url():
        """
        this static method returns the correct file path for the database.
        for development use DEBUG=True and the db is saved to /PROJECT_ROOT/.data
        """
        debug_mode = env.get("DEBUG", default=True)

        pd_dir = user_data_dir(appname="pi_duts", appauthor="lennik") if not debug_mode else path.abspath(
            path.join(path.dirname(path.realpath(__file__)), pardir, ".data"))

        makedirs(pd_dir, exist_ok=True)

        logger.info("Found the following data path: " +  path.join(pd_dir, 'db.sqlite'),)

        return f"sqlite:///{path.join(pd_dir, 'db.sqlite')}"

    @staticmethod
    def parse_cli_args():
        """this static method parses the given command line arguments and returns a corresponding Namespace object"""
        # main arg parser
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(dest="cmd")

        # user parser
        parser_user = subparsers.add_parser("users", help="Get user info")
        parser_user.add_argument("user_cmd", choices=["list", "add", "remove", "change_password"])
        parser_user.add_argument("--username", "-u", help="Username")

        # file parser
        parser_files = subparsers.add_parser("files", help="Get file info")
        parser_files.add_argument("file_cmd", choices=[None, "sync"], help="choose what to do with files")
        parser_files.add_argument("--username", "-u", help="Username", required=True)

        return parser.parse_args()

    def setup_db_and_run_migrations(self):
        """this static method sets up the database and runs migrations"""
        # get db url
        url_db = self.get_db_url()



        # run migrations and create db if not exist
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", url_db)
        print(path.join(path.dirname(path.realpath(__file__)), "migrations"))
        alembic_cfg.set_main_option("script_location",
                                    path.join(path.dirname(path.realpath(__file__)), "migrations"))

        logger.info("----- running migrations -----")
        command.upgrade(alembic_cfg, "head")
        logger.info("----- finished running migrations -----")

        self.engine = create_engine(url_db) # noqa

    def run(self):
        """this method runs pi_duts"""
        logging.basicConfig(level=logging.INFO)
        self.setup_db_and_run_migrations()

        cmd = self.parse_cli_args()

        logger.info(f"Got the following command: {cmd}")

        if cmd.cmd == "users":
            if cmd.user_cmd == "list":
                with Session(self.engine) as session:
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

                sync_dir = input(f"Enter directory to sync to if empty defaults to: {os.path.join(os.path.expanduser("~"), "PiDuts")}")

                if sync_dir.strip() == "":
                    sync_dir = path.join(os.path.expanduser("~"), "PiDuts")


                if not os.path.exists(os.path.abspath(os.path.join(sync_dir, os.pardir))):
                    raise ValueError("Directory does not exist")

                os.makedirs(sync_dir, exist_ok=True)

                user = User(username=username.strip(), base_url=url, sync_dir=sync_dir)

                with Session(self.engine) as session:
                    try:
                        session.add(user)
                        session.commit()
                        session.refresh(user)
                        logger.info(f"Successfully added user {username}")
                    except Exception as e:
                        session.rollback()
                        logger.error(e)

                keyring.set_password("pi_duts", str(user.id), password)
                check_pass = keyring.get_password("pi_duts", str(user.id))
                if check_pass == password:
                    logger.info("Password set successfully")



            elif cmd.user_cmd == "change_password":
                if cmd.username:
                    username = cmd.username
                else:
                    username = input("Username: ")
                password = getpass("Password: ",) # echo_char="*" for later python =< 3.14

                with Session(self.engine) as session:
                    user = session.query(User).filter(User.username == username).first()
                    if user:
                        user_id = user.id

                keyring.set_password("pi_duts", str(user_id), password)
                check_pass = keyring.get_password("pi_duts", str(user_id))
                if check_pass == password:
                    print("Password changed successfully")

            elif cmd.user_cmd == "remove":
                pass

        elif cmd.cmd == "files":
            if cmd.file_cmd == "sync":
                if not cmd.username:
                    logger.error("Please enter username")
                    exit(1)
                with Session(self.engine) as session:
                    user = session.query(User).filter(User.username == cmd.username).first()

                if not user:
                    logger.error("User not found")
                    exit(1)

                nav = Navigator(self.engine, user)







if __name__ == '__main__':
    PiDuts().run()
