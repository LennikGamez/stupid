from bs4 import BeautifulSoup
from navigator import Navigator

def get_tokens_from_login_page(nav: Navigator):
    """This function returns a tuple with the security_token as the first element and the login_ticket as the second element"""

    res = nav.loginpage().content
    bs = BeautifulSoup(res, "html.parser")
    form = bs.find(id="login-form")

    if not form:
        print("Could not find the login-form!")
        return ("", "")
    
    security_token_input = form.find(attrs={"name": "security_token"})
    if not security_token_input:
        print("Security Token was not found!")
        return ("", "")
    security_token = security_token_input.get("value")

    login_ticket_input = form.find(attrs={"name": "login_ticket"})
    if not login_ticket_input:
        print("Login Ticket was not found!")
        return ("", "")
    login_ticket = login_ticket_input.get("value")

    return security_token, login_ticket

def login(nav: Navigator, security_token, login_ticket, username, password):
    """After this function ran successfully the Navigator session is logged in"""
    return nav.post(nav.login_endpoint, data={
                 "loginname": username,
                 "password": password,
                 "security_token": security_token,
                 "login_ticket": login_ticket,
                 "resolution": "",
                 "Login": ""
             })
