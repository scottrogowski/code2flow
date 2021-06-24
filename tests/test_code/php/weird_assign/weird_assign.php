<?php

function a() {}
function b() {}

function c($x, $y) {
    [$integer, $remainder] = a(b($x), b((string) $y));

}

?>
