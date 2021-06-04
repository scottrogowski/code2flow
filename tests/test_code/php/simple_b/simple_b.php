<?php

require __DIR__.'/../vendor/autoload.php';

function a($param) {
    b($param);
}


function b() {
    a("STRC #");
}


class C {
    function d($param) {
        a("AnotherSTR");
    }
}

$c = new C();
$c->d();

?>
