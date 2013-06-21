import pysimple2
import testscripts.pysimple3
from pyfolder import *

obj = pysimple2.h()

obj.a()
testscripts.pysimple3.g()
pysimple4.infolderc()

def b():
	c()

def c():
	print 'this is c'

class e:
	def f():
		b()
		pysimple2.h.a()

e.f()