class Abra
    def magic()
    end

    def abra_it()
    end
end

class Cadabra
    def magic()
    end

    def cadabra_it(a: nil)
        a.abra_it()
    end
end

def main(cls)
    obj = cls.new()
    obj.magic()
    obj.cadabra_it()
end

main(Cadabra)
