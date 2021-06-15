const {myClass, inner, hi} = require("imported");

function outer() {
    let cls = new myClass();
    inner();
    hi();
}

outer();
