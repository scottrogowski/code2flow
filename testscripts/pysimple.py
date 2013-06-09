import pysimple2
import testscripts.pysimple3

pysimple2.a()
testscripts.pysimple3.g()

def b():
	c()

def c():
	print 'this is c'

class e:
	def f():
		b()
		pysimple2.h.a()

e.f()