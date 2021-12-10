<?php
// From https://www.w3schools.com/php/php_oop_access_modifiers.asp
class Fruit {
  public $name;
  public $color;
  public $weight;

  function set_name($n) {  // a public function (default)
    $this->name = $n;
  }
  protected function set_color($n) { // a protected function
    $this->color = $n;
  }
  private function set_weight($n) { // a private function
    $this->weight = $n;
  }
}

function set_color_weight($fruit) {
    $fruit.set_color('blue');
    $fruit.set_weight(5);
}

$fruit = new Fruit();
$fruit.set_name('blueberry');
set_color_weight();

?>
