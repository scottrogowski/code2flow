// from https://ruby-doc.com/docs/ProgrammingRuby/html/tut_modules.html

function majorNum() {}

function pentaNum() {}

class MajorScales {
  majorNum() {
    this.numNotes = 7;
    return this.numNotes;
  }
}

class FakeMajorScales {
  majorNum() {
    console.log("Not this one")
  }
}

class ScaleDemo extends MajorScales {
  constructor() {
    console.log(this.majorNum())
  }
}

let sd = new ScaleDemo();
pentaNum()
