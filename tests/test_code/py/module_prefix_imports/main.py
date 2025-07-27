import repository.user_repository as user_repository
from repository.user_repository import get_users2


def main():
    user_repository.get_users()
    get_users2()


main()