import logging
from os import path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, Engine

from cli import CLI
from constants import get_db_url

logger = logging.getLogger(__name__)

class Stupid:
    def __init__(self):
        # database engine as attribute
        self.engine: Engine

    def setup_db_and_run_migrations(self):
        """this static method sets up the database and runs migrations"""
        # get db url
        url_db = get_db_url()

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
        """this method runs stupid"""
        logging.basicConfig(level=logging.INFO)
        self.setup_db_and_run_migrations()

        cmd = CLI.parse_args()

        logger.info(f"Got the following command: {cmd}")

        if not cmd.gui:
            CLI(self.engine, cmd).run_cli()



if __name__ == '__main__':
    Stupid().run()
