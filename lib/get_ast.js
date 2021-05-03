const fs = require('fs');
const {Parser} = require("acorn")

const sourceType = process.argv[2]
const src = fs.readFileSync(process.argv[3], 'utf8')
//'ecmaVersion': '2019',
const tree = Parser.parse(src, {'locations': true, 'sourceType': sourceType})
const classFields = require('acorn-class-fields');


process.stdout.write(JSON.stringify(tree))
