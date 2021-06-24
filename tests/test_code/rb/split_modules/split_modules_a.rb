require_relative("split_modules_b")

def say_hi
end

def say_bye
end

module Split
    def self.say_hi
        puts "hi"
        say_bye
    end
end


obj = Split::MyClass.new()
obj.doit()
