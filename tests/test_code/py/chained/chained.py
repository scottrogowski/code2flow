class Chain():
    def __init__(self, val):
        self.val = val

    def add(self, b):
        self.val += b
        return self

    def sub(self, b):
        self.val -= b
        return self

    def mul(self, b):
        self.val *= b
        return self


print(Chain(5).add(5).sub(2).mul(10))
