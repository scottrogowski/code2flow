<?php
// from https://www.w3schools.com/php/php_oop_classes_abstract.asp

// Parent class
abstract class Car {
  public $name;
  public function __construct($name) {
    $this->name = $name;
  }
  abstract public function intro() : string;
}

// Interface
interface Noisy {
  public function makeSound();
}

// Child classes
class Audi extends Car implements Noisy {
  public function intro() : string {
    return "Choose German quality! I'm an $this->name!";
  }

  public function makeSound(): string {
    return "HONK!";
  }
}

class Volvo extends Car implements Noisy {
  public function intro() : string {
    return "Proud to be Swedish! I'm a $this->name!";
  }
  public function makeSound(): string {
    return "HONK!";
  }
}

class Citroen extends Car implements Noisy {
  public function intro() : string {
    return "French extravagance! I'm a $this->name!";
  }
}

// Create objects from the child classes
$audi = new Audi("Audi");
echo $audi->intro();
echo $audi->makeSound();
echo "<br>";

$volvo = new Volvo("Volvo");
echo $volvo->intro();
echo "<br>";

$citroen = new Citroen("Citroen");
echo $citroen->intro();
?>
