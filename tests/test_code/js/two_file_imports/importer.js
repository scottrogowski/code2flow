// import myClass from "imported"
// TODO this isn't actually being required correctly but it is testing
// a usecase. Add a better require to test its correct functionality
const {myClass, inner, hi} = require("imported");

function outer() {
    let cls = new myClass();
    inner();
    hi();
}

outer();
