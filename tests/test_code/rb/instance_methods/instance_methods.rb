def main
    puts("This is not called")
end

class Abra
    def main
        def nested
            puts("This will reference the main on Abra")
            main
        end
        nested
        puts("Hello from main")
    end

    def main2
        def nested2
            main()
        end
    end
end

a = Abra.new()
a.main()
a.nested()
a.main2()
a.nested2()
