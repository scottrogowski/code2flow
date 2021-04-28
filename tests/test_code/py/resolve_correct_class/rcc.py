def func_1():
    print("global func_1")


class Alpha():
    def func_1(self):
        print("alpha func_1")
        self.func_1()
        func_1()
        b = Beta()
        b.func_2()

    def func_2(self):
        print("alpha func_2")


class Beta():
    def func_1(self):
        print("beta func_1")
        al = Alpha()
        al.func_2()

    def func_2(self):
        print("beta func_2")
