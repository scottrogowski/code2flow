from re import (search, match)
import re.match as mitch


def main():
    a = b = search("abc", "def")
    c = mitch("abc", "def")
    return a, b, c


match("abc", "def")
main()
