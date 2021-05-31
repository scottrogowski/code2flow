class Chain {
    constructor(val) {
        this.val = val;
    }

    add(b) {
        this.val += b
        return this;
    }

    sub(b) {
        this.val -= b;
        return this;
    }

    mul(b) {
        this.val *= b;
        return this;
    }
}

console.log((new Chain(5)).add(5).sub(2).mul(10));
