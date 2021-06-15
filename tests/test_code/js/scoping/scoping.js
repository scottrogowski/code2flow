function scope_confusion() {
    console.log('scope_confusion');
}

class MyClass {
    scope_confusion() {
        console.log('scope_confusion');
    }

    a() {
        this.scope_confusion();
    }

    b() {
        scope_confusion();
    }
}


let obj = new myClass();
obj.a();
obj.b();
