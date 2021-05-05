def print_it(string):
    print(string)


def func_a():
    print_it("func_a")


def func_b():
    print_it("func_a")


def func_c():
    print_it("func_a")


func_dict = {
    'func_a': func_a,
    'func_b': func_b,
    'func_c': func_c,
}

func_dict['func_a']()
func_b()


def factory():
    return lambda x: x**x


factory()(5)
