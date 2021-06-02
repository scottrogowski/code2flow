"""
Comments
"""


def a()
    b()
end

# comments
def b()
    a("""STRC #""")
end

class Cls
    def initialize(val)
        @val = val
    end
    def d(a="String")
        a("AnotherSTR")
    end
end

c = Cls.new()
c.d()
