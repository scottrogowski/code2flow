def a
    puts "A"
    b
end

def b
    puts "B"
    a
end

class Cls
    def initialize
        puts "init"
    end

    def a
        puts "a"
        self
    end

    def b
        puts "b"
        return self
    end
end

def c
    obj = Cls.new()
    obj.a.b.a.c
end

a
b
c
