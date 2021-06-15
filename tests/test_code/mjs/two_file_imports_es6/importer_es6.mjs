import {myClass, inner} from "./imported_es6.mjs";

function outer() {
    let cls = new myClass();
    inner();
}

outer();
