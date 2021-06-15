
class ClsA {
    bark() {
        console.log("woof");
    }
}
class ClsB {
    meow() {
        console.log("meow");
    }
}

ClsA.B = ClsB;


class ClsC extends ClsA.B {}

let c = new ClsC();
c.meow();
