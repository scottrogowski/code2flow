class Abra {
    init() {
        return this.init()
    }
}

class Cadabra {
    init() {
        return this.init()
    }
}

function abra_fact() {
    return Abra;
}

function cadabra_fact() {
    return Cadabra;
}


class ClassMap {
    fact(which) {
        return which == "abra" ? abra_fact : cadabra_fact;
    }
}

obj = true ? new ClassMap.fact("abra").init(n) : new ClassMap.fact("cadabra").init(n)
obj = true ? new ClassMap.fact("abra").fact().init(n) : new ClassMap.fact("cadabra").fact().init(n)
