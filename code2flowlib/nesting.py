def extractBetween(string,delimiterA,delimiterB,startAt=0):
	'''
	Given a string and two delimiters, return the text between the first pair of delimiters after 'startAt'
	'''
	string = string[startAt:]
	delimSize = len(delimiterA)
	if delimSize != len(delimiterB):
		raise Exception("delimiterA must be the same length as delimiterB")

	start = string.find(delimiterA)
	if start == -1:
		return ''
	start += delimSize

	endPos = endDelimPos(string[start:],delimiterA,delimiterB)
	if endPos != -1:
		return string[start:start+endPos]
	else:
		return ''


def endDelimPos(string,delimiterA,delimiterB):
	delimSize = len(delimiterA)
	if delimSize != len(delimiterB):
		raise Exception("delimiterA must be the same length as delimiterB")

	count = 1
	i = 0
	while i<len(string) and count>0:
		tmp = string[i:i+delimSize]
		if tmp==delimiterA:
			count += 1
			i+=delimSize
		elif tmp==delimiterB:
			count -= 1
			i+=delimSize
		else:
			i+=1

	if count == 0:
		return i-delimSize
	else:
		return -1

def openBracketPos(pos):
	'''
	Go back to find the nearest open bracket without a corresponding close
	'''

	count = 0
	i = pos
	while i>=0 and count>=0:
		if string[i] in ('}',')'):
			count += 1
		elif string[i] in ('{','('):
			count -= 1
		i-=1

	if count==-1:
		return i+1
	else:
		return 0






class SourceFile:
	sourceStr = ''
	nestingBoundaries = {}

	def __init__(self,strorfile):
		if type(strorfile) == file:
			with open(strorfile) as f:
				self.sourceStr = f.read()
		elif type(strorfile) == str:
			self.sourceStr = strorfile

	def _calculateNesting(self):
		while i<len(self.sourceStr):
			pass

	def isGlobalScope(self,pos):
		return nestedLevel(pos) == 0

	def nestedLevel(self,pos):
		pass

