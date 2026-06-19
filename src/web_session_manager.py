from os import path
from logging import getLogger
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests as r
import pickle
import keyring

from constants import *

from users import User

logger = getLogger(__name__)

class WebSessionManager:
    def __init__(self, user: type[User], ensure_login: bool=True):
        self.user = user
        self.app_dir = get_app_dir()
        self.session = r.session()
        self.session_file = path.join(self.app_dir, f"session_user_{self.user.id}.pickle")
        self.ensure_login = ensure_login


    def __enter__(self):
        if path.exists(self.session_file):
            with open(self.session_file, "rb") as f:
                self.session.cookies.update(pickle.load(f))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self.session_file, "wb") as f:
            pickle.dump(self.session.cookies, f)

    def get(self, endpoint, use_base_url = True, base_url: str="",) -> r.Response:
        if base_url == "": base_url = self.user.base_url

        return self.session.get(urljoin(base_url, endpoint) if use_base_url else endpoint)

    def post(self, endpoint, data=None) -> r.Response:
        return self.session.post(urljoin(str(self.user.base_url), endpoint), data)

    def _extract_sec_token_from_loginpage(self) -> tuple[bool, tuple[str, str] | None]:
        res = self.get(EP_LOGIN).content
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

    def session_login(self) -> bool:
        tk_success, (tk_sec, tk_login) = self._extract_sec_token_from_loginpage()
        if not tk_success: return False

        res = self.post(EP_LOGIN, data={
             "loginname": self.user.username,
             "password": keyring.get_password("pi_duts", str(self.user.id)),
             "security_token": tk_sec,
             "login_ticket": tk_login,
             "resolution": "",
             "Login": ""
        })

        # save session cookies

        return True


