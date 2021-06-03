<?php

function main() {
    echo "main; This is called from abra.main";
}

class Abra {
    function main() {
        echo "Abra.main";
        function nested() {
            echo "Abra.nested; This gets placed on Abra";
            main(); # calls global main
        }
        $this->nested();
    }

    function main2() {
        echo "Abra.main2";
        function nested2() {
            echo "Abra.nested2";
            $this.main();
        }
    }
}

echo "A";
$a = new Abra();
echo "B";
$a.main();
echo "C";
$a.nested();
$a.main2();
$a.nested2();

?>
