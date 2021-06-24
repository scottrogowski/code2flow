
<?php

function func_a($name) {
    echo "Hello " + $name;
}

$greet = (static function($name): void
{
    func_a($name);
});

$greet('World');

?>

