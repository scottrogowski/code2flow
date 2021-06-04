# from https://ruby-doc.com/docs/ProgrammingRuby/html/tut_modules.html

from inherits_import import MajorScales, PentatonicScales


def majorNum():
    pass


def pentaNum():
    pass


class FakePentatonicScales():
    def pentaNum(self):
        if self.numNotes is None:
            self.numNotes = 5
        return self.numNotes


class ScaleDemo(MajorScales, PentatonicScales):
    def __init__(self):
        self.numNotes = None
        print(self.majorNum())
        print(self.pentaNum())

    def nothing(self):
        pass


class ScaleDemoLimited(MajorScales):
    def __init__(self):
        self.numNotes = None
        print(self.majorNum())


sd = ScaleDemo()
majorNum()
