<?php

// Nested functions in PHP are global so should be placed on the same scope

function outer() {
    echo "outer";
    function inner() {
        echo "inner";
    }
}

outer();
inner();

?>
