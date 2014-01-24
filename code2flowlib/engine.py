'''
This is the base module which is then subclassed by the language chosen

There are three basic graph elements defined:
Graph: 		Which represents namespaces or classes
Node:  		Which represents functions
Edge:  		Which represents function calls

Then, there are two other classes:
Sourcecode: An object to hold and manipulate the sourcecode
Mapper: 		Runs the show

The implementation files (javascript.py and python.py) subclass every one of these classes sometimes replacing functions and sometimes adding completely new functions

This way, we can share a lot of code between languages while still preserving full language flexibility

Functions that begin with an "_" are not replaced by any implementation
'''

import copy
import importlib
import operator
import os
import re
import pdb
import pprint

from mutablestring import MString

#for generating UIDs for groups and nodes
currentUID = 0

def generateEdges(nodes):
	'''
	When a function calls another function, that is an edge
	This is in the global scope because edges can exist between any node and not just between groups
	'''
	edges = []
	for node0 in nodes:
		for node1 in nodes:
			if DEBUG:
				print '"%s" links to "%s"?'%(node0.name,node1.name)
			if node0.linksTo(node1):
				if DEBUG:
					print "Edge created"
				edges.append(Edge(node0,node1))
	return edges

class Node(object):
	'''
	Nodes represent functions
	'''

	#How we know if a function returns
	returnPattern = re.compile(r"\Wreturn\W",re.MULTILINE)


	def __init__(self,name,definitionString,source,parent,fullSource=None,characterPos=0,lineNumber=0,isFileRoot=False): #allow default characterPos, lineNumber for implicit nodes
		#basic vars
		self.name = name
		self.definitionString = definitionString
		self.source = source
		self.fullSource=fullSource or source
		self.parent = parent
		self.characterPos = characterPos
		self.lineNumber = lineNumber #The line number the definition is on
		self.isFileRoot = isFileRoot

		#generate the name patterns for other nodes to search for this one
		self.pattern = re.compile(r"(?:\W|\A)(%s)\s*\("%self.name,re.MULTILINE)  # The name pattern which is found by others eg. node()

		self.determineNodeType() # Init node, etc.

		self.sameScopePatterns = self.generateSameScopePatterns()  # The pattern to search for when the other node is in the same scope e.g. self.node()
		self.namespacePatterns = self.generateAnyScopePatterns() # The pattern to search for with the namespace eg. Node.node()

		#determine whether there are return statements or not
		self.returns = self.returnPattern.search(self.source.sourceString)

		#increment the identifier
		#Needed for the sake of a unique node name for graphviz
		global currentUID
		self.uid = currentUID
		currentUID += 1

		#Assume it is a leaf and a trunk until determined otherwise
		self.isLeaf = True #it calls nothing else
		self.isTrunk = True #nothing calls it



	def generateSameScopePatterns(self):
		return [re.compile(r"(?:\W|\A)%s\.%s\s*\("%(self.sameScopeKeyword,self.name),re.MULTILINE|re.DOTALL)]

	def generateAnyScopePatterns(self):
		return [
			re.compile(r"(?:[^a-zA-Z0-9\.]|\A)%s\s*\("%(self.getFullName()),re.MULTILINE|re.DOTALL)
			]

	def getNamespace(self):
		return self.parent.getNamespace()

	def determineNodeType(self):
		'''
		Dummy meant to be subclassed if we do extra calculations to determine node type
		'''
		self.isInitNode = False


	def getFullName(self):
		'''
		Return the name with the namespace
		'''
		namespace = self.getNamespace()
		if '/' in namespace:
			namespace = namespace.rsplit('/',1)[1]

		return namespace+'.'+self.name if namespace else self.name

	def linksTo(self,other):
		raise NotImplementedError

	def contains(self,other):
		return other.linksTo(self)

	def isExtraneous(self,edges=None):
		'''
		Dummy function meant to be subclassed
		Will contain logic that will determine whether this node can be removed during trimming
		'''
		return False

	def _getUID(self):
		return 'node'+str(self.uid)
	def _getFileGroup(self):
		return self.parent._getFileGroup()

	def _getFileName(self):
		return self.parent._getFileName()

	def __str__(self):
		'''
		For printing to the DOT file
		'''
		attributes = {}

		attributes['label']="%d: %s"%(self.lineNumber,self.getFullName())
		attributes['shape']="rect"
		attributes['style']="rounded"
		#attributes['splines']='ortho'
		if self.isTrunk:
			attributes['style']+=',filled'
			attributes['fillcolor']='coral'
		elif self.isLeaf:
			attributes['style']+=',filled'
			attributes['fillcolor']='green'

		ret = self._getUID()
		if attributes:
			ret += ' [splines=ortho '
			for a in attributes:
				ret += '%s = "%s" '%(a,attributes[a])
			ret += ']'

		return ret


class Edge(object):
	'''
	Edges represent function calls
	'''
	def __init__(self,node0,node1):
		self.node0 = node0
		self.node1 = node1

		#When we draw the edge, we know the calling function is definitely not a leaf...
		#and the called function is definitely not a trunk
		node0.isLeaf = False
		node1.isTrunk = False

	def __str__(self):
		'''
		For printing to the DOT file
		'''
		ret = self.node0._getUID() + ' -> ' + self.node1._getUID()
		if self.node1.returns:
			ret += ' [color="blue" penwidth="2"]'
		return ret

	def hasEndNode(self,node1):
		return node1 == self.node1

	def hasStartNode(self,node0):
		return node0 == self.node0

class Group(object):
	'''
	Groups represent namespaces
	'''

	def __init__(self,name,source,fullSource=None,definitionString='',parent=None,lineNumber=0,**kwargs):
		self.name = name
		self.definitionString = definitionString
		self.source = source
		self.fullSource = fullSource or source
		self.parent = parent
		self.lineNumber = lineNumber

		self.nodes = []
		self.subgroups = []

		#So that we can track object calls as well like:
		# a = Obj()
		# a.b()
		self.newObjectPattern = self.generateNewObjectPattern()
		self.newObjectAssignedPattern = self.generateNewObjectAssignedPattern()

		#increment the identifier
		#Needed for the sake of a unique node name for graphviz
		global currentUID
		self.uid = currentUID
		currentUID += 1

	def __str__(self):
		'''
		__str__ is for printing to the DOT file
		'''
		#pdb.set_trace()
		ret = 'subgraph '+self._getUID()
		ret += '{\n'
		if self.nodes:
			for node in self.nodes:
				ret += node._getUID() + ' '
				#if node.isFileRoot:
				#	ret += ";{rank=source; %s}"%node._getUID()

			ret += ';\n'
		ret += 'label="%s";\n'%self.name;
		ret += 'style=filled;\n';
		ret += 'color=black;\n';
		ret += 'graph[style=dotted];\n'
		#pdb.set_trace()
		for subgroup in self.subgroups:
			ret += str(subgroup)
		ret += '}'
		return ret

	def getNamespace(self):
		'''
		Returns the full string namespace of this group including this groups name
		'''
		#TODO more complex namespaces involving parents and modules
		#js implements something a bit more complicated already
		#python uses this

		return self.name

	def trimGroups(self):
		pass

	def _generateRootNodeName(self,name=''):
		if not name:
			name = self.name
		return "(%s %s frame (runs on import))"%(name,self.globalFrameName)


	def _pprint(self,printHere=True):
		'''
		Print the file structure
		Strictly for debugging right now
		'''
		tree = map(lambda x:(x.name,'node'),self.nodes)
		tree += map(lambda x:(x.name,x._pprint(printHere=False)),self.subgroups)
		if printHere:
			pprint.pprint(dict(tree))
		else:
			return dict(tree)


	def _getUID(self):
		'''
		Something
		'''
		try:
			if self.isAnon:
				return 'clusterANON'+str(self.uid)
			else:
				raise Exception()
		except:
			return 'cluster'+re.sub(r"[/\.\-\(\)=\s]",'',self.name)+str(self.uid)

	def _allNodes(self):
		'''
		Every node in this namespace and all descendent namespaces
		'''
		nodes = self.nodes
		for subgroup in self.subgroups:
			nodes += subgroup._allNodes()
		return nodes

	def _getFileGroup(self):
		if self.parent:
			return self.parent._getFileGroup()
		else:
			return self

	def _getFileName(self):
		return self._getFileGroup().name


class SourceCode(object):
	'''
	SourceCode is a convenient object object representing:
		source text (sourceString)
		a line number array (characterToLineMap)

	A sourcecode object is maintained internally in both the Group and Node and classes

	Implementations will probably only have to overwrite the two properties:
		blockComments
		strings
	Although Python does overwrite more because of it's indent system

	The sourcecode object supports the following primitive operations
		sc = SourceCode()
		len(sc) #characters
		sc[a:b] #betweenCharacters
		sc[a] #character
		scA + scB #addition as long as line numbers do not overlap
		scA - scB #subtraction as long as scB is completely inside scA
		sc == True #truth testing (empty string)
		str(sc) print with line numbers

	And these are the methods
		copy() #deepcopy
		firstLineNumber() #of the entire object
		lastLineNumber()  #of the entire object
		remove(string) #and return new sourcecode
		pop() #return last line
		getPosition(lineNumber) #get character index at linenumber
		getLineNumber(characterPos) #get line number of character
		find(what,start) #run sourceString.find()
		extractBetweenDelimiters(a,b,startAt) #return new sourcecode between the first pair of delimiters after startAt
		getSourceInBlock(bracketPos) #Return the source to the matching bracket
		matchingBracketPos(bracketPos) #Return the matching bracket position
		endDelimPos(startAt,a,b) #return the position of the nearest end bracket given a position in the block
		openDelimPos(startAt) #return the position of the nearest begin bracket given a position in the block
		_removeCommentsAndStrings() #called on init. Does as it says changing the object

	'''

	#These two must be subclassed
	blockComments = []
	inlineComments = ''
	delimA='{'
	delimB='}'

	def __init__(self,sourceString,characterToLineMap=None):
		'''
		Remove the comments and build the linenumber/file mapping while doing so
		'''
		self.sourceString = sourceString

		if characterToLineMap:
			self.characterToLineMap = characterToLineMap
		else:
			self.characterToLineMap = {}

			self._removeCommentsAndStrings()
			self.sourceString = str(self.sourceString) #convert back to regular python string from mutable string

			if DEBUG:
				#print 'REMOVED COMMENTS',self
				with open('cleanedSource','w') as outfile:
					outfile.write(self.sourceString)

		self.delimLen = len(self.delimA)

	def __len__(self):
		return len(self.sourceString)

	def __getitem__(self,sl):
		'''
		If sliced, return a new object with the sourceString and the characterToLineMap sliced by [firstChar:lastChar]

		1. Slice the source string in the obvious way.
		2. Slice the charactertolinemap
			a. Remove character mappings that are not in between where we are shifting to
			b. Take remaining characterPositions and shift them over by start shift

		'''
		if type(sl) == int:
			return self.sourceString[sl]

		if type(sl) != slice:
			raise Exception("Slice was not passed")

		if sl.step and (sl.start or sl.stop):
			raise Exception("Sourcecode slicing does not support the step attribute (e.g. source[from:to:step] is not supported)")

		if sl.start is None:
			start = 0
		else:
			start = sl.start

		if sl.stop is None:
			stop = len(self.sourceString)
		elif sl.stop < 0:
			stop = len(self.sourceString)+sl.stop
		else:
			stop = sl.stop

		if start>stop:
			raise Exception("Begin slice cannot be greater than end slice. You passed SourceCode[%d:%d]"%(sl.start,sl.stop))

		ret = self.copy()

		ret.sourceString = ret.sourceString[start:stop]

		#filter out character mapping we won't be using
		shiftedCharacterToLineMap = {}
		characterPositions = ret.characterToLineMap.keys()
		characterPositions = filter(lambda p: p>=start and p<=stop,characterPositions)

		#shift existing character mappings to reflect the new start position
		#If we start with 0, no shifting will take place
		for characterPosition in characterPositions:
			shiftedCharacterToLineMap[characterPosition-start] = ret.characterToLineMap[characterPosition]

		#we need this to be sure that we can always get the line number no matter where we splice
		shiftedCharacterToLineMap[0] = self.getLineNumber(start)

		ret.characterToLineMap = shiftedCharacterToLineMap
		return ret

	def __add__(self,other):
		'''
		Add two pieces of sourcecode together shifting the character to line map appropriately
		'''

		#If one operand is nothing, just return the value of this operand
		if not other:
			return self.copy()

		if self.lastLineNumber()>other.firstLineNumber():
			raise Exception("When adding two pieces of sourcecode, the second piece must be completely after the first as far as line numbers go")

		sourceString = self.sourceString + other.sourceString

		shiftedCharacterToLineMap = {}
		characterPositions = other.characterToLineMap.keys()
		for characterPosition in characterPositions:
			shiftedCharacterToLineMap[characterPosition+len(self.sourceString)] = other.characterToLineMap[characterPosition]

		characterToLineMap = dict(self.characterToLineMap.items() + shiftedCharacterToLineMap.items())

		ret = SourceCode(sourceString=sourceString,characterToLineMap=characterToLineMap)

		return ret

	def __sub__(self,other):
		if not other:
			return self.copy()

		if self.firstLineNumber()>other.firstLineNumber() or self.lastLineNumber()<other.lastLineNumber():
			pdb.set_trace()
			raise Exception("When subtracting a piece of one bit of sourcecode from another, the second must lie completely within the first")

		firstPos = self.sourceString.find(other.sourceString)

		if firstPos == -1:
			pdb.set_trace()
			raise Exception('Could not subtract string starting with "%s" from source because string could not be found'%other.sourceString[:50].replace("\n","\\n"))

		lastPos = firstPos + len(other.sourceString)


		firstPart = self[:firstPos]

		secondPart = self[lastPos:]

		return firstPart+secondPart

	def __nonzero__(self):
		'''
		__nonzero__ is object evaluates to True or False
		sourceString will be False when the sourceString has nothing or nothing but whitespace
		'''
		return self.sourceString.strip()!=''

	def __str__(self):
		'''
		Mostly for debugging. Print the source with line numbers
		'''
		ret = ''
		for i, char in enumerate(self.sourceString):
			if i in self.characterToLineMap:
				ret += '%d: '%self.characterToLineMap[i]
			ret += char
		return ret

	def copy(self):
		return copy.deepcopy(self)

	def firstLineNumber(self):
		'''
		First line number of the entire source
		'''
		try:
			return min(self.characterToLineMap.values())
		except ValueError:
			raise Exception("Sourcecode has no line numbers")

	def lastLineNumber(self):
		'''
		Last line number of the entire source
		'''
		try:
			return max(self.characterToLineMap.values())
		except ValueError:
			raise Exception("Sourcecode has no line numbers")

	def remove(self,stringToRemove):
		'''
		Remove a string. Does not alter object in place
		'''
		firstPos = self.sourceString.find(stringToRemove)
		if firstPos == -1:
			pdb.set_trace()
			raise Exception("String not found in source")
		lastPos = firstPos + len(stringToRemove)
		return self[:firstPos]+self[lastPos:]

	def pop(self):
		'''
		Pop off the last line
		'''
		lastLinePos = self.sourceString.rfind('\n')
		ret = self.sourceString[lastLinePos:]
		self = self[:lastLinePos]

		return ret

	def getPosition(self,lineNumberRequest):
		'''
		From lineNumber, get the character position
		'''
		for pos,lineNumber in self.characterToLineMap.items():
			if lineNumber == lineNumberRequest:
				return pos

		raise Exception("Could not find line number in source")

	def getLineNumber(self,pos):
		'''
		Decrement until we find the first character of the line and can get the linenumber
		'''
		while True:
			try:
				return self.characterToLineMap[pos]
			except:
				pos-=1
				if pos < 0:
					raise Exception("could not get line number for position %d"%pos)

	def find(self,what,start=0):
		'''
		Pass through 'find' makes implementations cleaner
		'''
		return self.sourceString.find(what,start)

	def extractBetweenDelimiters(self,startAt=0):
		'''
		Return the source between the first pair of delimiters after 'startAt'
		'''

		start = self.sourceString.find(self.delimA,startAt)
		if start == -1:
			return None
		start += self.delimLen

		endPos = self.endDelimPos(start,self.delimA,self.delimB)
		if endPos != -1:
			return self[start:endPos]
		else:
			return None

	def getSourceInBlock(self,bracketPos):
		'''
		Get the source within two matching brackets
		'''
		otherBracketPosition = self.matchingBracketPos(bracketPos)

		if bracketPos < otherBracketPosition:
			startBracketPos = bracketPos
			endBracketPos = otherBracketPosition
		else:
			startBracketPos = otherBracketPosition
			endBracketPos = bracketPos

		ret = self[startBracketPos+1:endBracketPos]
		return ret

	def matchingBracketPos(self,bracketPos):
		'''
		Find the matching bracket position
		'''

		delim = self[bracketPos]
		if delim == self.delimA:
			if self.sourceString[bracketPos+1]==self.delimB:
				return bracketPos + 1
			else:
				return self.endDelimPos(startAt=bracketPos+1)
		elif delim == self.delimB:
			if self.sourceString[bracketPos-1]==self.delimA:
				return bracketPos - 1
			else:
				return self.openDelimPos(startAt=bracketPos-1)
		else:
			raise Exception('"%s" is not a known delimiter'%delim)

	def endDelimPos(self,startAt):
		'''
		Find the nearest end delimiter assuming that 'startAt' is inside of a block
		'''

		count = 1
		i = startAt
		while i<len(self.sourceString) and count>0:
			tmp = self.sourceString[i:i+self.delimLen]
			if tmp==self.delimA:
				count += 1
				i+=self.delimLen
			elif tmp==self.delimB:
				count -= 1
				i+=self.delimLen
			else:
				i+=1

		if count == 0:
			return i-self.delimLen
		else:
			return -1

	def openDelimPos(self,pos):
		'''
		Find the nearest begin delimiter assuming that 'pos' is inside of a block
		TODO there is probably no reason why this also includes parenthesis
		TODO this should probably just be the same function as endDelimPos
		'''

		count = 0
		i = pos
		while i>=0 and count>=0:
			if self.sourceString[i] in ('}',')'):
				count += 1
			elif self.sourceString[i] in ('{','('):
				count -= 1
			i-=1

		if count==-1:
			return i+1
		else:
			return 0

	def _removeCommentsAndStrings(self):
		'''

		Two things happen here:
		a. Character by character, add those characters which are not part of comments or strings to a new string
		   Same the new string as the 'sourceString' variable
		b. At the same time, generate an array of line number beginnings called the 'characterToLineMap'

		This uses a mutable string to save time on adding

		'''
		print "Removing comments and strings..."

		originalString = str(self.sourceString)
		self.sourceString = MString('')
		self.characterToLineMap = {}
		lineCount = 1
		self.characterToLineMap[0] = lineCount #character 0 is line #1
		lineCount += 1 #set up for next line which will be two
		#pdb.set_trace()
		i=0

		inlineCommentLen = len(self.inlineComments)

		#begin analyzing charactes 1 by 1 until we reach the end of the originalString
		#-blockCommentLen so that we don't go out of bounds
		while i < len(originalString):
			#check if the next characters are a block comment
			#There are multiple types of block comments so we have to check them all
			for blockComment in self.blockComments:
				if type(blockComment['start']) == str:
					blockCommentLen = len(blockComment['start'])
					if originalString[i:][:blockCommentLen] == blockComment['start']:
						#if it was a block comment, jog forward
						prevI = i
						i = originalString.find(blockComment['end'],i+blockCommentLen)+blockCommentLen

						while originalString[i-1]=='\\':
							i = originalString.find(blockComment['end'],i+blockCommentLen)+blockCommentLen

						if i==-1+blockCommentLen:
							#if we can't find the blockcomment and have reached the end of the file
							#return the cleaned file
							return

						#increment the newlines
						lineCount+=originalString[prevI:i].count('\n')

						#still want to see the comments, just not what is inside
						self.sourceString.append(blockComment['start'] + blockComment['end'])

						break
				else:
					#is a regex blockcomment... sigh js sigh...
					match = blockComment['start'].match(originalString[i:])
					if match:
						#print match.group(0)
						#print originalString[i-5:i+5]
						prevI = i

						endMatch = blockComment['end'].search(originalString[i+match.end(0):])

						if endMatch:
							i = i+match.end(0)+endMatch.end(0)
						else:
							return

						#increment the newlines
						lineCount+=originalString[prevI:i].count('\n')
						break
			else:
				#check if the next characters are an inline comment
				if originalString[i:][:inlineCommentLen] == self.inlineComments:
					#if so, find the end of the line and jog forward. Add one to jog past the newline
					i = originalString.find("\n",i+inlineCommentLen+1)

					#if we didn't find the end of the line, that is the end of the file. Return
					if i==-1:
						return
				else:
					#Otherwise, it is not a comment. Add to returnstr
					self.sourceString.append(originalString[i])

					#if the originalString is a newline, then we must note this
					if originalString[i]=='\n':
						self.characterToLineMap[len(self.sourceString)] = lineCount
						lineCount += 1
					i+=1


class Mapper(object):
	'''
	The primary class of the engine which gets called first
	Mapper is meant to be abstract and subclassed by various languages
	'''

	SINGLE_QUOTE_PATTERN = re.compile(r'(?<!\\)"')
	DOUBLE_QUOTE_PATTERN = re.compile(r"(?<!\\)'")

	files = {}

	def __init__(self,implementation,files):
		'''
		Two things are happening:
		1. We are overwriting all of the classes with the implementation's classes
			So if we are working with a javascript file, the implementation variable points to javascript.py
			Then, we overwrite every class in engine.py with all of the javascript.py's classes
		2. We are loading the source files into the mapper class
		'''

		global Node,Edge,Group,Mapper,SourceCode
		Node = implementation.Node
		Edge = implementation.Edge
		Group = implementation.Group
		Mapper = implementation.Mapper
		SourceCode = implementation.SourceCode

		for f in files:
			with open(f) as fi:
				self.files[f] = fi.read()


	def map(self):
		'''
		I. For each file passed,
			1. Generate the sourcecode for that file
			2. Generate a group from that file's sourcecode
				a. The group init will recursively generate all of the subgroups and function nodes for that file
		II.  Trim the groups bascially removing those which have no function nodes
		III. Generate the edges
		IV.  Return the file groups, function nodes, and edges
		'''

		#get the filename and the fileString
		#only first file for now
		nodes = []
		fileGroups = []
		for filename,fileString in self.files.items():
			#remove .py from filename
			filename = self.simpleFilename(filename)
			print "Mapping %s"%filename

			#generate sourcecode (remove comments and add line numbers)
			source = SourceCode(fileString)

			#Create all of the subgroups (classes) and nodes (functions) for this file
			print "Generating function nodes..."
			fileGroup = self.generateFileGroup(name=filename,source=source)
			fileGroups.append(fileGroup)

			#Append nodes generated to all nodes
			nodes += fileGroup._allNodes()

		#Trimming the groups mostly removes those groups with no function nodes
		for group in fileGroups:
			group.trimGroups()
			if DEBUG:
				print "Post trim, %s"%group.name
				group._pprint()

		#Figure out what functions map to what
		print "Generating edges..."
		edges = generateEdges(nodes)

		#Trim off the nodes (mostly global-frame nodes that don't do anything)
		finalNodes = []
		for node in nodes:
			if not node.isExtraneous(edges):
				finalNodes.append(node)
			else:
				node.parent.nodes.remove(node)
				del node


		#return everything we have done
		return fileGroups,finalNodes,edges

	def generateFileGroup(self,name,source):
		'''
		Dummy function probably superclassed
		This will initialize the global group for the entire source file
		'''
		return Group(name=name,source=source)

	def simpleFilename(self,filename):
		'''
		Return the filename without the path
		'''
		if '.' in filename:
			filename = filename[:filename.rfind('.')]

		return filename
