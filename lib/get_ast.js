const fs = require('fs');
const {Parser} = require("acorn")

const src = fs.readFileSync(process.argv[2], 'utf8')
const tree = Parser.parse(src, {'locations': true, 'ecmaVersion': '2019', 'sourceType': "script"})
const classFields = require('acorn-class-fields');


process.stdout.write(JSON.stringify(tree))
