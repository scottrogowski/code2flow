<?php

function func_b() {
    echo "hello world";
}

function func_a() {
    func_b();
}

func_a();

?>
