class Abra():
    def magic():
        pass

    def abra_it():
        pass


class Cadabra():
    def magic():
        pass

    def cadabra_it(a=None):
        a.abra_it()


def main(cls):
    obj = cls()
    obj.magic()
    obj.cadabra_it()


main()
