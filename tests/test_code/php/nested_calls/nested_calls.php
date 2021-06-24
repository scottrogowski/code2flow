<?php

function x_() {
    (new Cls()).func2();
}
function y_() {}
function z_() {}

function func() {}
function func2() {}


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
        $amount = x_(y_(z_($amount), z_('1' . str_pad('', $decimalPlaces, '0'))));
    }
}

(new Cls()).func();

func2()

?>
