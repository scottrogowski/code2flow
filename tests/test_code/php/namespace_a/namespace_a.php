<?php
namespace NS;

function namespaced_func() {
    echo "namespaced_func";
}

class Namespaced_cls {
    function __construct() {
        echo "__construct";
    }
    function instance_method() {
        echo "instance_method";
    }
}

namespaced_func();
$a = new Namespaced_cls();
$a->instance_method();

?>
