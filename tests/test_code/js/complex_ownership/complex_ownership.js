class ABC {
    constructor() {
        this.b = 5;
    }
    doit() {
        let _this = this;
        return _this.b;
    }
    apply() {
        return 5;
    }
    ret_def() {
        return DEF
    }
}

class DEF {
    toABC() {
        calls = 5;
        return new ABC();
    }
}

class GHI {
    doit2(varname) {
        return varname.apply()
    }
    doit3() {
        console.log("");
    }
}

var empty_var;
var double_decl = [], empty_var;
calls = 5;
let abc = new DEF();
abc.toABC().doit(calls);

new GHI().doit2()
var inp = AbsentClass()
inp.a.b.c.apply(null, arguments);

var jsism = (function() {
    return "no other language does this crazy nonsense";
})()

var jsism_2 = (function() {
    return "no other language does this crazy nonsense";
}).anything()


var obj_calls = {
    'abc': ABC,
    'def': DEF,
    'ghi': GHI,
}
obj_calls['ghi'].doit3();

// This below shouldn't match anything because it's too complex of a constructor
var def = new abc.ret_def()
