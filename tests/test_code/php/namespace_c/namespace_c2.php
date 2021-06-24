<?php

namespace Outer\Inner;

function speak() {
    echo "global speak";
}

class Cat {
    static function meow() {
        echo "cat meow";
    }
    static function speak() {
        echo "cat speak";
    }
}

class Dog {
    static function meow() {
        echo "dog meow";
    }
    static function speak() {
        echo "dog speak";
    }
}


?>
