<?php

require_once("namespace_b2.php");
use foo;
use foo as feline;

// namespaced_func();
// $a = new Namespaced_cls();
// $a->instance_method();

echo \foo\Cat::meows(), "<br />\n";
echo \feline\Cat::says(), "<br />\n";

use animate;
echo \animate\Animal::meows(), "<br />\n";


?>
