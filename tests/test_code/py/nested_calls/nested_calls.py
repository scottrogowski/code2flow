from typing import Callable

def trace(fn: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        print('traced call')
        return fn(*args, **kwargs)
    return wrapper

def do_something(msg):
    return msg + ' world'

message = 'hello'
new_message = trace(do_something)(message)
