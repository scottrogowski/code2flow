from infrastructure import http
from infrastructure.http import request


def get_users():
    http.request("GET", "https://api.example.com/users")


def get_users2():
    request("GET", "https://api.example.com/users")