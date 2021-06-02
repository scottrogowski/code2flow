class Mod
    def func_1
        puts("func_1 outer")
    end

    def func_2
        puts("func_2 outer")
    end

    class Nested
        def initialize
            puts("hello world")
            func_1
        end
        def func_1
            puts("func_1")
            Mod::func_1
        end
        def func_2
            puts("func_2")
            func_1()
            Mod::func_2
        end
    end
end

def func_1
    puts("func_1 top_level")
    func_2
end

def func_2
    puts("func_2 top_level")
    func_1
end

obj = Mod::Nested.new()
obj.func_2()
outer_obj = Mod.new()
outer_obj.func_1()
