<?php
function func_1() {
    echo "this should never get called";
}

class Alpha {
    function func_1() {
        echo "alpha func_1";
        $this.func_1();
        $b = new Beta();
        $b->func_2();
    }

    function func_2() {
        echo "alpha func_2";
    }
}

class Beta {
    function func_1() {
        echo "beta func_1";
        $al = new Alpha();
        $al->func_2();
    }

    function func_2() {
        echo "beta func_2";
    }
}
?>
