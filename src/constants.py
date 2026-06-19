from logging import getLogger
from os import environ as env
from os import path, makedirs, pardir
from appdirs import user_data_dir

logger = getLogger(__name__)

# endpoints
EP_LOGIN = "/dispatch.php/login"
EP_START = "/dispatch.php/start/index"
EP_COURSES = "/dispatch.php/my_courses"
EP_MESSAGES_OVERVIEW = "/dispatch.php/messages/overview"
EP_FILE_DIR_PAGE = "/dispatch.php/course/files?cid="
EP_FILE_FLAT_PAGE = "/dispatch.php/course/files/flat?cid="
EP_DOWNLOAD_NEWEST_FILES = "/dispatch.php/course/files/newest_files?cid="


def get_app_dir():
    debug_mode = env.get("DEBUG", default=True)

    pd_dir = user_data_dir(appname="pi_duts", appauthor="lennik") if not debug_mode else path.abspath(
        path.join(path.dirname(path.realpath(__file__)), pardir, ".data"))

    makedirs(pd_dir, exist_ok=True)

    logger.info("Found the following data path: " + pd_dir, )

    return pd_dir


def get_db_url():
    """
    this static method returns the correct file path for the database.
    for development use DEBUG=True and the db is saved to /PROJECT_ROOT/.data
    """
    return f"sqlite:///{path.join(get_app_dir(), 'db.sqlite')}"