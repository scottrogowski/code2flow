class DivByTwo
    def initialize(val: 0)
        @val = val
    end

    def +(val)
        @val += (val / 2)
        self
    end

    def -(val)
        @val -= (val / 2)
        self
    end

    def *(val)
        @val *= (val / 2)
        self
    end

    def result()
        @val
    end
end

num = DivByTwo.new(val: 5)
puts ((num + 5 - 5) * 5).result

puts 5 + 6 + 3
