const fs = require('fs');
const {Parser} = require("acorn")

const sourceType = process.argv[2]
const src = fs.readFileSync(process.argv[3], 'utf8')
const tree = Parser.parse(src, {'locations': true, 'sourceType': sourceType,
                                'ecmaVersion': '2020'})

process.stdout.write(JSON.stringify(tree))
