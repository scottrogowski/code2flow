# def func_a
#     puts "global func_a"
# end

# def func_b
#     puts "global func_b"
# end

class Class1
    def self.func_a
        Class2::func_b()
        puts "Class1::func_a"
    end

    def self.func_b
        func_a()
        puts "Class1::func_b"
    end
end


class Class2
    def self.func_a
        Class1::func_b()
        puts "Class2::func_a"
    end

    def self.func_b
        func_a()
        puts "Class2::func_b"
    end
end

a = 5
Class2::func_b
