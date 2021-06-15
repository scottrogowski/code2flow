class Abra {
    constructor() {
        this.abra_it();
        }
    magic() {
        console.log('magic 1');
    }

    abra_it() {

    }
}


class Cadabra {
    magic() {
        console.log('magic 2');
    }

    cadabra_it(a) {
        let b = a.abra_it()
        let c = "d"
    }
}

function main(cls) {
    obj = cls()
    obj.magic()
    obj.cadabra_it()
}

main()
