//Node/CommonJS
const fs = require('fs')
const {readFile, chmod} = require('fs')


function readFileSync() {
    console.log("This is the local readFileSync");
}


function beta() {
    print("this still connects")
    readFileSync()
    b = Nothing()
    b.beta()
    chmod();
}


function alpha() {
    fs.readFileSync("exclude_modules.js");
    beta()
    match()
    alpha()
}


alpha()
module.exports = {alpha}
