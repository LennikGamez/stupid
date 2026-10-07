import logging

from web_session_manager import WebSessionManager

logger = logging.getLogger(__name__)

# Endpoints

API_VERSION = "/jsonapi.php/v1"
USER_INFO = API_VERSION + "/users/me"
course_list = API_VERSION + "/users/<user-id>/courses"
class ApiNavigator:
    # Endpoints
    def __init__(self, wsm: WebSessionManager ):
        self.wsm = wsm

    def get_user_info_via_session_token(self):
        res = self.wsm.get(USER_INFO)
        json_data = res.json()
        return json_data.get("data").get("id") # stud_id


