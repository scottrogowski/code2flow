class Outer():
    class Inner():
        def inner_func():
            Outer().outer_func()

    def outer_func(a):
        print("Outer_func")
        a.inner_func()

    def __init__(self):
        self.inner = self.Inner()
        print("do something")


new_obj = Outer()
new_obj.outer_func()
