//CommonJS
const fs = require('fs')
const {readFile, chmod} = require('fs')


//ECMA
// const msg = import('msg')
// import msg_pub from 'msg.js'
// import msg_pub as alias from 'msg.js'


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
}


alpha()
module.exports = {alpha}
