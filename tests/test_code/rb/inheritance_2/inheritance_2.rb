# from https://launchschool.com/books/oo_ruby/read/inheritance

def speak
  puts "WOOF"
end

class Animal
  def speak
    puts "Hello!"
  end
end

class GoodDog < Animal
end

class Cat < Animal
  def meow
    speak
  end
end

sparky = GoodDog.new
paws = Cat.new
puts sparky.speak
puts paws.meow
