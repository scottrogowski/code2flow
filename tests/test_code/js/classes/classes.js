function print_hi() {
    console.log("HI")
}

class Rectangle {
  constructor(height, width) {
    this.height = height;
    this.width = width;
    this.i = 0;
    print_hi();
    this.calcArea()
  }
  calcArea() {
    this.incr();
    return this.height * this.width
  }
  incr() {
    this.i++;
  }
}

function do_calc() {
    const the_area = square.calcArea()
    calcit()
    const square = new Rectangle(10, 10);
}

const do_calc_wrapper = function() {
    console.log("BANANAS")
    do_calc();
}

const square = new Rectangle(10, 10);
square.calcArea()
do_calc_wrapper()
