class myClass {
    constructor() {
        this.doit();
    }

    doit() {
        this.doit2();
    }

    doit2() {
        console.log('at the end')
    }
}

function inner() {
    console.log("inner")
}

export {myClass, inner};
