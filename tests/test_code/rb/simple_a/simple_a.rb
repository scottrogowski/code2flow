def func_b(var)
    puts "hello world"
end

def func_a()
    func_b()
end

func_a()
