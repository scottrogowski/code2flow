<?php
// namespace NSA {

//     function namespaced_func() {
//         echo "namespaced_func";
//     }

//     class Namespaced_cls {
//         function __construct() {
//             echo "__construct";
//         }
//         function instance_method() {
//             echo "instance_method";
//         }
//     }
// }

// namespace NSB {

//     function namespaced_func() {
//         echo "namespaced_func";
//     }

//     class Namespaced_cls {
//         function __construct() {
//             echo "__construct";
//         }
//         function instance_method() {
//             echo "instance_method";
//         }
//     }
// }

namespace animate {
    class Animal {
        static function breathes() {echo 'air';}
        static function meows() {echo 'meoow2';}
    }
}

namespace bar {
    class Dog {
        static function says() {echo 'ruff';}
    }
}

namespace foo {
    use animate;
    class Cat extends animate\Animal {
        static function says() {echo 'meoow';}
        static function meows() {echo 'meoow2';}

    }
}

?>
