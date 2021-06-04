 <?php

function say_name() {}

class Greeting {
  public static function welcome() {
    echo "Hello World!";
  }

  function say_name() {
    echo $this->name;
  }

  function __construct($name) {
      $this->name = $name;
      echo self::welcome() + ' ' + $this->say_name();
  }
}

function welcome() {}

// Call static method
Greeting::welcome();
$greet = new Greeting("Scott");
?>
