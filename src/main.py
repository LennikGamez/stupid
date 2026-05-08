from os.path import join

from alembic import command
from alembic.config import Config
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy.testing.config import db_url

from models import User
from navigator import Navigator
from login import get_tokens_from_login_page, login
from argparse import ArgumentParser
from os import makedirs, environ as env
from appdirs import user_data_dir
from sqlalchemy import create_engine, text, Engine
from os import path, getcwd, pardir
from getpass import getpass
import keyring
import logging

logger = logging.getLogger(__name__)

"""domain = input("Domain: ")
username = input("Username: ")
password = input("Password: ")

nav = Navigator(domain)
security_token, login_ticket = get_tokens_from_login_page(nav)
res = login(nav, security_token, login_ticket, username, password)
print(BeautifulSoup(res.content, "html.parser").prettify)
print("You are now logged in :)")"""

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
        debug_mode = env.get("DEBUG", default=False)

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

        self.engine = create_engine(url_db)

    def run(self):
        """this method runs pi_duts"""
        logging.basicConfig(level=logging.INFO)
        self.setup_db_and_run_migrations()

        cmd = self.parse_cli_args()

        if cmd.cmd == "users":
            if cmd.user_cmd == "list":
                with Session(self.engine) as session:
                    users = session.query(User).all()

                for u in users:
                    print(u.username)

            elif cmd.user_cmd == "add":
                print("Please enter details for adding user")
                username = input("Username: ")

                user = User(username=username.strip(), base_url="", sync_dir="")

                with Session(self.engine) as session:
                    try:
                        session.add(user)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        logger.error(e)

            elif cmd.user_cmd == "change_password":
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

        elif cmd.cmd == "files":
            pass



if __name__ == '__main__':
    PiDuts().run()
