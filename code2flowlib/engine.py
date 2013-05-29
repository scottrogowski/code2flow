'''
The main logic goes here.
This is the base module which is then partially overwritten by the language chosen

There are three basic modules defined:
Graphs: which represent namespaces
Nodes:  which represent functions
Edges:  which represent function calls
'''

import copy
import operator
import os
import re
import pdb
import pprint

from nesting import *

DEBUG = True

currentUID = 0

def generateEdges(nodes):
	'''
	When a function calls another function, that is an edge
	'''
	edges = []
	for node0 in nodes:
		for node1 in nodes:
			if node0 != node1 and node0.linksTo(node1):
				edges.append(Edge(node0,node1))
	return edges

class Node(object):
	'''
	Nodes represent functions
	'''
	returnPattern = re.compile(r"\Wreturn\W",re.MULTILINE)

	namespaceBeforeDotPattern = re.compile(r'[^\w\.]([\w\.]+)\.$',re.MULTILINE)

	def __init__(self,name,definitionString,source,parent,lineNumber):
		#basic vars
		self.name = name
		self.definitionString = definitionString
		self.source = source
		self.parent = parent
		self.lineNumber = lineNumber #The line number the definition is on

		#generate the name patterns for other nodes to search for this one
		self.pattern = re.compile(r"\W(%s)\s*\("%self.name,re.MULTILINE)  # The name pattern which is found by others eg. node()

		self.determineNodeType() # Init node, etc.

		self.sameScopePatterns = self.generateSameScopePatterns()  # The pattern to search for when the other node is in the same scope e.g. self.node()
		self.namespacePatterns = self.generateNamespacePatterns() # The pattern to search for with the namespace eg. Node.node()

		#just whether there are return statements or not
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
		return [re.compile(r"\W%s\.%s\s*\("%(self.sameScopeKeyword,self.name))]

	def generateNamespacePatterns(self):
		return [re.compile(r"\W%s\.%s\s*\("%(self.parent.getNamespace(),self.name))]

	def getFileGroup(self):
		return self.parent.getFileGroup()

	def getFileName(self):
		return self.parent.getFileName()

	def linksTo(self,other):
		#print self.name," links to ",other.name,'?'

		importNamespace = ''

		#If this is in a different file, figure out what namespace to use
		if self.getFileGroup() != other.getFileGroup():
			importPaths = other.parent.getImportPaths(self.getFileName())

			for importPath in importPaths:
				regularImport = re.compile(r"^import\s%s\s*$"%re.escape(importPath),re.MULTILINE)
				complexImport = re.compile('^from\s%s\simport\s(?:\*|(?:.*?\W%s\W.*?))\s*$'%(re.escape(importPath),re.escape(other.name)),re.MULTILINE)
				#print importPath
				#print self.parent.getFileGroup().name
				if regularImport.search(self.getFileGroup().source.sourceString):
					importNamespace += importPath
					break
				elif complexImport.search(self.getFileGroup().source.sourceString):
					break
			else:
				return False

			#namespacePrefix =

		#If the naive functionName (e.g. \Wmyfunc\( ) appears anywhere in this sourceString, check whether it is actually THAT function
		match = other.pattern.search(self.source.sourceString)
		if match:
			matchPos = match.start(1)
			hasDot = self.source.sourceString[matchPos-1] == '.'

			#if the other function is in the global namespace and this call is not referring to any namespace, return true
			if not other.parent.parent and not hasDot: #TODO js will require the 'window' namespace integrated somehow
				return True

			#if the other is part of a namespace and we are looking for a namspace
			if other.parent.parent and hasDot:

				#try finding the namespace of the called object
				try:
					prefixSearchLine = self.source.sourceString[:matchPos].split('\n')[-1]
					#print '"%s"'%prefixSearchLine
					namespace = self.namespaceBeforeDotPattern.search(prefixSearchLine).group(1)
				except AttributeError:
					#will not find a namespace if the object is in an array or something else weird
					#fall through this function because we can still check for init node
					namespace = None

				#If the namespaces are the same, that is a match
				if namespace == importNamespace + other.name and self.getFileGroup() == other.getFileGroup():
					return True

				#if they are part of the same namespace, we can check for the 'self' keyword
				if other.parent == self.parent and namespace == self.sameScopeKeyword:
					return True

				#If a new object was created prior to this call and that object calls this function, that is a match
				newObjectMatch = other.parent.newObjectAssignedPattern.search(self.source.sourceString)
				if newObjectMatch and namespace == importNamespace + newObjectMatch.group(1):
					return True


		#TODO put in try in case isInitNode not defined
		if other.isInitNode and other.parent.newObjectPattern.search(self.source.sourceString):
			return True

		return False

	'''
	def linksTo(self,other):
		print self.name," links to ",other.name,'?'
		#if self.parent.name == "SourceCode":
		#	pdb.set_trace()
		if other.parent:
			#if the other is part of a namespace
			if other.parent == self.parent:
				#if they are part of the same namespace, we can use the self keyword
				if any(map(lambda pattern: pattern.search(self.source.sourceString), other.sameScopePatterns)):
					return True

			#They can always be linked by their namespace
			if any(map(lambda pattern: pattern.search(self.source.sourceString), other.namespacePatterns)):
				return True
		else:
			#if other is part of the global namespace, we just search for its pattern
			if other.pattern.search(self.source.sourceString):
				return True
		return False
	'''

	def contains(self,other):
		return other.linksTo(self)

	'''
	def setGroup(self,group):
		self.group = group
		self.thisPattern = re.compile(r"\Wthis\.%s\s*\("%self.name,re.MULTILINE)
		print r"\Wthis\.%s\s*\("%self.name
		self.nameSpacePattern = re.compile(r"\W%s\.%s\s*\("%(self.group.name,self.name),re.MULTILINE)
		print r"\W%s\.%s\s*\("%(self.group.name,self.name)
	'''

	def getUID(self):
		return 'node'+str(self.uid)

	def __str__(self):
		'''
		For printing to the DOT file
		'''
		attributes = {}
		attributes['label']="%d: %s"%(self.lineNumber,self.name)
		if self.isTrunk:
			attributes['style']='filled'
			attributes['fillcolor']='brown'
		elif self.isLeaf:
			attributes['style']='filled'
			attributes['fillcolor']='green'

		ret = self.getUID()
		if attributes:
			ret += ' ['
			for a in attributes:
				ret += '%s = "%s" '%(a,attributes[a])
			ret += ']'
		return ret

class Edge:
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
		ret = self.node0.getUID() + ' -> ' + self.node1.getUID()
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


	def __init__(self,name,definitionString,source,parent=None,**kwargs):
		self.name = name
		self.definitionString = definitionString
		self.source = source
		self.parent = parent

		self.nodes = []
		self.subgroups = []

		self.newObjectPattern = self.generateNewObjectPattern()
		self.newObjectAssignedPattern = self.generateNewObjectAssignedPattern()

		#TODO can we get rid of this?
		self.validObj = True


	def __str__(self):
		'''
		__str__ is for printing to the DOT file
		'''
		ret = 'subgraph '+self.getUID()
		ret += '{\n'
		if self.nodes:
			for node in self.nodes:
				ret += node.getUID() + ' '
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

	def getUID(self):
		return 'cluster'+self.name.replace('/','').replace('.','')

	def allNodes(self):
		'''
		Every node in this namespace and all descendent namespaces
		'''
		nodes = self.nodes
		for subgroup in self.subgroups:
			nodes += subgroup.allNodes()
		return nodes

	def getFileGroup(self):
		if self.parent:
			return self.parent.getFileGroup()
		else:
			return self

	def getFileName(self):
		return self.getFileGroup().name

	def getNamespace(self):
		'''
		called by children nodes to generate their namespaces
		'''
		#if parent:
		#TODO more complex namespaces involving parents
		return self.name

	def insideGroup(self,pos):
		if self.start<pos and pos<self.end:
			return True
		else:
			return False

	def addNode(self,node):
		self.nodes.append(node)


	def getImportPaths(self,importerFilename):
		'''
		Return the relative and absolute paths the other filename would use to import this module
		'''

		#split paths into their directories
		thisFullPath = os.path.abspath(self.getFileName())
		importerFullPath = os.path.abspath(importerFilename)
		thisFullPathList = thisFullPath.split('/')
		importerFullPathList = importerFullPath.split('/')

		#pop off shared directories
		while True:
			try:
				assert thisFullPathList[0] == importerFullPathList[0]
				thisFullPathList.pop(0)
				importerFullPathList.pop(0)
			except:
				break


		paths = []

		relativePath = ''

		#if the importer's unique directory path is longer than 1,
		#then we will have to back up a bit to the last common shared directory
		relativePath += '.'*len(importerFullPathList)

		#add this path from the last common shared directory
		relativePath += '.'.join(thisFullPathList)

		paths.append(relativePath)

		#TODO there are probably more. We are getting
		#import languagages.python
		#but not
		#import code2flow.languages.python
		#but this will require knowing how far back we need to go
		paths.append('.'.join(thisFullPathList[-2:-1]))

		if len(importerFullPathList) == 1 and len(thisFullPathList) == 1:
			paths.append(thisFullPathList[-1])

		return paths

	def generateImplicitNodeName(self):
		return "%s-level (might run on import)"%self.implicitName

	def generateImplicitNodeSource(self):
		'''
		Find all of the code not in any subnode, string it together, and return it as the implicit node
		'''

		source = self.source
		for node in self.nodes:
			source-=node.source
			source =source.remove(node.definitionString)

		for group in self.subgroups:
			source-=group.source
			if group.definitionString:
				source = source.remove(group.definitionString)

		return source





class Mapper(object):
	'''
	Mappers are meant to be abstract and subclassed by various languages
	'''
	REWORD = r"(\w+[a-zA-Z])\W"
	REWORDPATH = r"\S+"

	REPARENTFUNCTION = r"\s+(\w+[a-zA-Z])\W"

	SINGLE_QUOTE_PATTERN = re.compile(r'(?<!\\)"')
	DOUBLE_QUOTE_PATTERN = re.compile(r"(?<!\\)'")


	def cleanFilename(self,filename):
		if '.' in filename:
			filename = filename[:filename.rfind('.')]

		return filename

	def stringsToEmpty(self):
		'''
		i=0
		while i < len(fileAsString):
			if fileAsString[i]=='\\':
				i += 2
			elif singleQuote.match(fileAsString[i:]):
				try:
					i = re.search(r'[^\\]"',fileAsString[i:]).end(0)
				except Exception, e:
					print fileAsString[i:i+100]
					print e
			elif doubleQuote.match(fileAsString[i:]):
				i = re.search(r"[^\\]'",fileAsString[i:]).end(0)
			else:
				fStr += fileAsString[i]
				i+=1
		'''



	def generateNode(self,reMatch,fileStr,nodeType=None):
		if nodeType == 'anonymous':
			name = '(anonymous parameter)'
		else:
			if reMatch.group(1):
				group=1
			else:
				group=2
			name = reMatch.group(group)

		if DEBUG:
			print 'generateNode: %s'%name

		content = extractBetween(fileStr,'{','}',reMatch.end(0)-1) #-1 b/c we might be on the bracket otherwise
		lineNumber = self.getLineNumber(reMatch.end(0))
		return Node(name,content,lineNumber)

	#TODO return False was just to get past mootools errors
	def generateGroup(self,bracketPos,fileStr,node):
		reversePool = fileStr[:bracketPos][::-1]
		match = re.search(self.REWORD,reversePool)

		#if not match:
		#	return Node(validObj = False)

		try:
			if match.group(1)=='prototype'[::-1]:
				match = re.search(self.REWORD,reversePool[match.end(1):])
			if match.group(1)=='function'[::-1]:
				match = re.search(self.REWORD,reversePool[match.end(1):])
		except:
			return False

		try:
			name = match.group(1)[::-1]
		except:
			return False

		nodes = [node]
		start = bracketPos
		end = endDelimPos(fileStr[start+1:],'{','}')+start+1

		return Group(name=name,nodes=nodes,start=start,end=end)





class SourceCode(object):
	'''
	SourceCode is a representation of source text and a character to linenumber/file mapping
	The mapping must be kept consistent when SourceCode is sliced

	A sourcecode object is maintained internally in both Group and Node
	'''


	def __init__(self,sourceString,characterToLineMap=None):
		'''
		Remove the comments and build the linenumber/file mapping whild doing so
		'''
		self.sourceString = sourceString

		if characterToLineMap:
			self.characterToLineMap = characterToLineMap
		else:
			self.characterToLineMap = {}

			self.removeComments()
			if DEBUG:
				print 'REMOVED COMMENTS',self

		#pprint.pprint(self.characterToLineMap)


	def __getitem__(self,sl):
		'''
		If sliced, return a new object with the sourceString and the characterToLineMap sliced by [firstChar:lastChar]
		'''

		if type(sl) != slice or sl.step:
			raise Exception("Sourcecode slicing does not support the step attribute (e.g. source[from:to:step] is not supported)")

		if sl.start is None:
			start = 0
		else:
			start = sl.start

		if sl.stop is None:
			stop = len(self.sourceString)
		else:
			stop = sl.stop

		ret = copy.deepcopy(self)

		ret.sourceString = ret.sourceString[start:stop]

		#print 'new source',ret.sourceString


		#update the chacter positions of the line breaks up to the end of the source
		shiftedCharacterToLineMap = {}
		characterPositions = ret.characterToLineMap.keys()
		characterPositions = filter(lambda p: p>=start and p<stop,characterPositions)
		for characterPosition in characterPositions:
			shiftedCharacterToLineMap[characterPosition-start] = ret.characterToLineMap[characterPosition]
		ret.characterToLineMap = shiftedCharacterToLineMap
		return ret

	def __add__(self,other):
		if not other:
			return copy.deepcopy(self)

		if self.lastLineNumber()>other.firstLineNumber():
			pdb.set_trace()
			raise Exception("When adding two pieces of sourcecode, the second piece must be completely after the first as far as line numbers go")

		sourceString = self.sourceString + other.sourceString

		shiftedCharacterToLineMap = {}
		characterPositions = other.characterToLineMap.keys()
		for characterPosition in characterPositions:
			shiftedCharacterToLineMap[characterPosition+len(self.sourceString)] = other.characterToLineMap[characterPosition]

		characterToLineMap = dict(self.characterToLineMap.items() + shiftedCharacterToLineMap.items())

		ret = SourceCode(sourceString,characterToLineMap)
		#pdb.set_trace()

		return ret

	def __sub__(self,other):
		return self.subtractSource(other)

	def remove(self,stringToRemove):
		firstPos = self.sourceString.find(stringToRemove)
		if firstPos == -1:
			raise Exception("String not found in source")
		lastPos = firstPos + len(stringToRemove)

		#pdb.set_trace()
		return self[:firstPos]+self[lastPos:]

	def subtractSource(self,other):
		if not other:
			return copy.deepcopy(self)

		if self.firstLineNumber()>other.firstLineNumber() or self.lastLineNumber()<other.lastLineNumber():
			pdb.set_trace()
			raise Exception("When subtracting a piece of one bit of sourcecode from another, the second must lie completely within the first")

		firstPos = self.sourceString.find(other.sourceString)

		if firstPos == -1:
			raise

		lastPos = firstPos + len(other.sourceString)


		firstPart = self[:firstPos]

		secondPart = self[lastPos:]

		return firstPart+secondPart


	def __nonzero__(self):
		return self.sourceString.strip()!=''

	def firstLineNumber(self):
		return min(self.characterToLineMap.values())

	def lastLineNumber(self):
		return max(self.characterToLineMap.values())

	def pop(self):
		lastLinePos = self.sourceString.rfind('\n')
		ret = self.sourceString[lastLinePos:]
		self = self[:lastLinePos]

		return ret


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
					pdb.set_trace()

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

	def removeComments(self):
		'''
		Character by character, add those characters which are not part of comments to the return string
		Also generate an array of line number beginnings
		'''
		originalString = self.sourceString
		self.sourceString = ''
		self.characterToLineMap = {}
		lineCount = 1
		self.characterToLineMap[0] = lineCount #character 0 is line #1
		lineCount += 1 #set up for next line which will be two

		i=0
		blockCommentLen = len(self.blockComments[0]['start'])
		inlineCommentLen = len(self.inlineComments)

		#begin analyzing charactes 1 by 1 until we reach the end of the originalString
		#-blockCommentLen so that we don't go out of bounds
		while i < len(originalString)-blockCommentLen:
			#check if the next characters are a block comment
			#There are multiple types of block comments so we have to check them all
			for blockComment in self.blockComments:
				if originalString[i:][:blockCommentLen] == blockComment['start']:
					#if it was a block comment, jog forward
					prevI = i
					i = originalString.find(blockComment['end'],i+blockCommentLen)+blockCommentLen
					#pdb.set_trace()
					if i==-1:
						#if we can't find the blockcomment and have reached the end of the file
						#return the cleaned file
						return

					#increment the newlines
					lineCount+=originalString[prevI:i].count('\n')
					break
			else:
				#check if the next characters are an inline comment
				if originalString[i:][:inlineCommentLen] == self.inlineComments:
					#if so, find the end of the line and jog forward
					i = originalString.find("\n",i+inlineCommentLen)

					#if we didn't find the end of the line, that is the end of the file. Return
					if i==-1:
						return
					lineCount += 1
				else:
					#Otherwise, it is not a comment. Add to returnstr
					self.sourceString += originalString[i]

					#if the originalString is a newline, then we must note this
					if originalString[i]=='\n':
						self.characterToLineMap[len(self.sourceString)] = lineCount
						lineCount += 1

					i+=1
		#print "generated charactertolinemap",self.characterToLineMap
		#print "sorterd lines",sorted(self.characterToLineMap.values())