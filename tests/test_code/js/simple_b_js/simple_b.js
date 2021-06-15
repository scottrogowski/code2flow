

function a() {
    b();
}


function b() {
    a("STRC #");
}


class C {
    d(param) {
        a("AnotherSTR");
    }
}

const c = new C()
c.d()
