<?php

function x() {}

function y() {}

function z() {}


class Cls {
    static function a($ret) {
        echo $ret;
    }
    static function b($ret) {
        echo $ret;
    }
    static function c($ret) {
        echo $ret;
    }


    function func() {
        self::a(self::b(self::c()));
    }

    function func2() {
        $amount = x(y(z($amount), z('1' . str_pad('', $decimalPlaces, '0'))));
    }
}

(new Cls()).func();

$a.func2()

?>
