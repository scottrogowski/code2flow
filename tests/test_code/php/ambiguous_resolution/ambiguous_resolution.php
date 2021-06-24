<?php

class Abra {
    function magic() {
        echo "Abra.magic() cant resolve";
    }
    function abra_it() {
        echo "Abra.abra_it() will resolve";
    }
}


class Cadabra {
    function magic() {
        echo "Cadabra.magic() cant resolve";

    }
    function cadabra_it($a) {
        echo "Cadabra.cadabra_it() will resolve";
        $a->abra_it();
        $a->magic();
    }
}


function main($cls) {
    echo "main";
    $obj = new $cls;
    $obj->magic();
    $obj->cadabra_it(new Abra());
}

main(Cadabra::class);

?>
