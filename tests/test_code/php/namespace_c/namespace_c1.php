<?php
require_once("namespace_c2.php");

use function Outer\Inner\speak as sp;
use Outer\Inner\Cat as Ct;

sp();
Ct::meow();


?>
