
<?php


$greet = (static function($name): void
{
    printf("Hello %s\r\n", $name);
})('World');

$saybye = (static function($name): void
{
    printf("Bye %s\r\n", $name);
});

$saybye('World');

function a() {}
a();
?>

