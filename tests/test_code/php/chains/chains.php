<?php
function a() {
    echo "A";
    b();
}


function b() {
    echo "B";
    a();
}


class Cls {
    function __construct() {
        echo "init";
        return $this;
    }


    function a() {
        echo "a";
        return $this;
    }

    function b() {
        echo "b";
        return $this;
    }
}


function c() {
    $obj = new Cls();
    $obj->a()->b()->a();
}

a();
b();
c();
?>
