class Rectangle {
  constructor(height, width) {
    this.height = height;
    this.width = width;
  }
  get area() {
    return this.calcArea();
  }
  calcArea() {
    return this.height * this.width
  }
}

function do_calc() {
    console.log("calcing... ")
    the_area = square.calcArea()
    calcit()
    const square = new Rectangle(10, 10);
}

const doc = function() {
    do_calc()
}

const square = new Rectangle(10, 10);
square.calcArea()

doc()
