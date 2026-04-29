import requests as req

class Navigator:
    def __init__(self, base_url):
        """The Navigator class takes a base_url in the constructor which is just the domain of your University's page"""
        self.base_url = base_url
        self.session = req.Session()

        self.login_endpoint = "/dispatch.php/login"
        self.start_endpoint = "/dispatch.php/start/index"
        self.courses_endpoint = "/dispatch.php/my_courses"
        self.messages_overview_endpoint = "/dispatch.php/messages/overview"

    def get(self, endpoint):
        return self.session.get(self.base_url + endpoint)

    def post(self, endpoint, data={}):
        return self.session.post(self.base_url + endpoint, data)

    def loginpage(self) -> req.Response:
        return self.get(self.login_endpoint)
        
    def coursespage(self) -> req.Response:
        return self.get(self.courses_endpoint)
    
