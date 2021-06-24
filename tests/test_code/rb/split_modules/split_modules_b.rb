module Split

    class MyClass
        def initialize
            puts "initialize"
        end

        def doit
            puts "doit"
            Split::say_hi
        end
    end

    def self.say_bye
        puts "bye"
    end
end
