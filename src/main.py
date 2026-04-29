from bs4 import BeautifulSoup
from navigator import Navigator
from login import get_tokens_from_login_page, login

domain = input("Domain: ")
username = input("Username: ")
password = input("Password: ")

nav = Navigator(domain)
security_token, login_ticket = get_tokens_from_login_page(nav)
res = login(nav, security_token, login_ticket, username, password)
print(BeautifulSoup(res.content, "html.parser").prettify)
print("You are now logged in :)")
