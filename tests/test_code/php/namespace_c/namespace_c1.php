<?php
require_once("namespace_c2.php");

use function Outer\Inner\speak as talk;
use Outer\Inner\Cat as Kitty;

talk();
Kitty::meow();


?>
