def func_1
    puts "this should never get called"
end

class Alpha
    def func_1()
        puts "alpha func_1"
        self.func_1()
        func_1()
        b = Beta.new()
        b.func_2()
    end

    def func_2()
        puts "alpha func_2"
    end
end

class Beta
    def func_1()
        puts "beta func_1"
        al = Alpha.new()
        al.func_2()
    end

    def func_2()
        puts "beta func_2"
    end
end
