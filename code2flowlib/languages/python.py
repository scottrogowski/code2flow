'''
All of these classes subclass engine.py classes

Functions that begin with an "_" are local and do not replace anything in engine.py
'''

from code2flowlib.engine import *

indentPattern = re.compile(r"^([\t ]*)\S",re.MULTILINE)
def getIndent(colonPos,sourceString):
	try:
		return indentPattern.search(sourceString[colonPos:]).group(1)
	except:
		pdb.set_trace()

class Node(Node):
	sameScopeKeyword = 'self'
	namespaceBeforeDotPattern = re.compile(r'(?:[^\w\.]|\A)([\w\.]+)\.$',re.MULTILINE)

	def generateSameScopePatterns(self):
		patterns = super(Node,self).generateSameScopePatterns()
		return patterns

	def generateNamespacePatterns(self):
		patterns = super(Node,self).generateNamespacePatterns()
		if self.name == '__init__':
			pattern = re.compile(r"\W%s\("%self.parent.getNamespace())
			patterns.append(pattern)
		#if self.name == '__str__':
		#	pattern = re.compule(r"\Wstr\(\s*%s\s*\)"%self.
		return patterns

	def determineNodeType(self):
		if self.name == '__init__':
			self.isInitNode = True
		else:
			self.isInitNode = False

	def isExtraneous(self,edges):
		'''
		Returns whether we can safely delete this node
		'''
		if self.isRoot():
			for edge in edges:
				if edge.node0 == self or edge.node1 == self:
					return False
			else:
				return True
		return False

	def isRoot(self):
		if self.parent.parent:
			return False
		else:
			return True

	def linksTo(self,other):

		importNamespace = ''

		#If this is in a different file, figure out what namespace to use
		if self._getFileGroup() != other._getFileGroup():
			importPaths = other.parent.getImportPaths(self._getFileName())

			for importPath in importPaths:
				regularImport = re.compile(r"^import\s+%s\s*$"%re.escape(importPath),re.MULTILINE)
				complexImport = re.compile('^from\s%s\simport\s(?:\*|(?:.*?\W%s\W.*?))\s*$'%(re.escape(importPath),re.escape(other.name)),re.MULTILINE)
				#print importPath
				#print self.parent._getFileGroup().name
				if regularImport.search(self._getFileGroup().source.sourceString):
					importNamespace += importPath
					break
				elif complexImport.search(self._getFileGroup().source.sourceString):
					break
			else:
				return False

		if not other.isRoot():
			importNamespace = importNamespace + '.' + other.parent.name if importNamespace else other.parent.name

		#If the naive functionName (e.g. \Wmyfunc\( ) appears anywhere in this sourceString, check whether it is actually THAT function
		match = other.pattern.search(self.source.sourceString)
		if match:
			matchPos = match.start(1)
			hasDot = self.source.sourceString[matchPos-1] == '.'

			#if the other function is in the global namespace and this call is not referring to any namespace, return true
			if other.isRoot() and not hasDot: #TODO js will require the 'window' namespace integrated somehow
				return True

			#if the other is part of a namespace and we are looking for a namspace
			if hasDot:

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
				if namespace == importNamespace:# and self._getFileGroup() == other._getFileGroup(): #+ other.name
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

class Edge(Edge):
	pass

class Group(Group):

	classPattern = re.compile(r"^class\s(\w+)\s*(\(.*?\))?\s*\:",re.MULTILINE)
	#implicitName = 'module'

	globalFrameName = 'module'

	def __init__(self,indent='',**kwargs):
		'''
		Generate a new group

		The only thing special about groups in python is they are delimited by indent
		This makes things a little bit easier
		'''
		self.indent = indent

		super(Group,self).__init__(**kwargs)

		#If this is the root node, set indent to nothing
		#if not self.parent:
		#	self.indent = ''

		#with the indent set, we can now generate nodes
		self._generateNodes()

		#If this is the root node, continue generating subgroups and nodes
		if not self.parent:
			self.generateSubgroups()
			self.nodes.append(self.generateRootNode())

	def trimGroups(self):
		pass

	def _generateNodes(self):
		'''
		Find all function definitions, generate the nodes, and append them
		'''
		functionPatterns = self.generateFunctionPatterns()
		for pattern in functionPatterns:
			functionMatches = pattern.finditer(self.source.sourceString)
			for functionMatch in functionMatches:
				node = self.generateNode(functionMatch)
				self.nodes.append(node)

	def generateFunctionPatterns(self):
		'''
		Return the regex for function definition at this indent level
		'''
		indent = self.indent.replace(' ',r'\s').replace('	',r'\t')
		return [re.compile(r"^%sdef\s(\w+)\s*\(.*?\)\s*\:"%indent,re.MULTILINE|re.DOTALL)]

	def generateSubgroups(self):
		classMatches = self.classPattern.finditer(self.source.sourceString)
		for classMatch in classMatches:
			name = classMatch.group(1)
			definitionString = classMatch.group(0)
			colonPos = classMatch.end(0)
			indent = getIndent(colonPos=colonPos,sourceString=self.source.sourceString)
			source = self.source.getSourceInBlock(colonPos=colonPos)
			fullSource = self.source.getSourceInBlock(colonPos=colonPos,fullSource=True)
			lineNumber = self.source.getLineNumber(colonPos)
			classGroup = Group(name=name,definitionString=definitionString,indent=indent,source=source,fullSource=fullSource,parent=self,lineNumber=lineNumber)
			self.subgroups.append(classGroup)

	def generateNewObjectPattern(self):
		return re.compile(r'%s\s*\('%self.name)

	def generateNewObjectAssignedPattern(self):
		return re.compile(r'(\w)\s*=\s*%s\s*\('%self.name)

	def generateRootNode(self):
		name = self._generateRootNodeName()
		source = self.generateImplicitNodeSource()
		return Node(name=name,definitionString=None,source=source,parent=self) #isImplicit=True

	def generateImplicitNodeSource(self):
		'''
		Find all of the code not in any subnode, string it together, and return it as the implicit node
		'''

		source = self.source.copy()
		for node in self.nodes:
			source -= node.fullSource

			#source =source.remove(node.definitionString)

		for group in self.subgroups:
			source -= group.fullSource
			'''
			source.remove(group.source.sourceString)
			if group.definitionString:
				#print group.definitionString

				source = source.remove(group.definitionString)
			'''
		return source

	def getImportPaths(self,importerFilename):
		'''
		Return the relative and absolute paths the other filename would use to import this module
		'''
		paths = self._getRelativeImportPaths(importerFilename)+self._getAbsoluteImportPaths()
		return paths


	def _getRelativeImportPaths(self,importerFilename):
		#split paths into their directories
		thisFullPath = os.path.abspath(self._getFileName())
		thisFullPathList = thisFullPath.split('/')

		importerFullPath = os.path.abspath(importerFilename)
		importerFullPathList = importerFullPath.split('/')

		#pop off shared directories
		while True:
			try:
				assert thisFullPathList[0] == importerFullPathList[0]
				thisFullPathList.pop(0)
				importerFullPathList.pop(0)
			except AssertionError:
				break

		relativePath = ''

		#if the importer's unique directory path is longer than 1,
		#then we will have to back up a bit to the last common shared directory
		relativePath += '.'*len(importerFullPathList)

		#add this path from the last common shared directory
		relativePath += '.'.join(thisFullPathList)
		paths = []

		paths.append(relativePath)

		try:
			paths.append(thisFullPathList[-2:-1][0])
		except:
			pass

		return paths

	def _getAbsoluteImportPaths(self):
		paths = []

		pathArray = os.path.realpath(self._getFileName()).split('/')[::-1]
		buildPathList = pathArray[0]
		pathArray = pathArray[1:]

		paths.append(buildPathList)
		for elem in pathArray:
			if elem:
				buildPathList = elem + '.' + buildPathList
				paths.append(buildPathList)

		return paths

	def generateNode(self,reMatch):
		'''
		Using the name match, generate the name, source, and parent of this node

		group(0) is the entire definition line ending at the new block delimiter like:
			def myFunction(a,b,c):
		group(1) is the identifier name like:
			myFunction
		'''
		name = reMatch.group(1)
		definitionString = reMatch.group(0)

		newBlockDelimPos = reMatch.end(0)
		beginIdentifierPos = reMatch.start(1)

		source = self.source.getSourceInBlock(newBlockDelimPos)
		fullSource = self.source.getSourceInBlock(newBlockDelimPos,fullSource=True)
		lineNumber = self.source.getLineNumber(beginIdentifierPos)
		return Node(name=name,definitionString=definitionString,source=source,fullSource=fullSource,parent=self,characterPos=beginIdentifierPos,lineNumber=lineNumber)


class SourceCode(SourceCode):
	blockComments = [
		{'start':'"','end':'"'}
		,{'start':"'",'end':"'"}
		,{'start':"'''",'end':"'''"}
		,{'start':'"""','end':'"""'}
		]
	inlineComments = "#"

	def getSourceInBlock(self,colonPos,fullSource=False):
		'''
		Overwrites superclass method
		'''
		indent = getIndent(colonPos,self.sourceString)

		endPos = colonPos

		lines = self.sourceString[colonPos:].split('\n')[1:]
		for line in lines:
			if line.startswith(indent) or line.strip()=='':
				endPos += len(line)+1 #+1 for the newlines lost
			else:
				break

		if fullSource:
			startPos = self.sourceString.rfind('\n',0,colonPos)
			if startPos == -1:
				startPos = 0
			else:
				startPos += 1
		else:
			startPos = colonPos+1
		try:
			return self[startPos:endPos]
		except:
			pdb.set_trace()


class Mapper(Mapper):

	def generateFileGroup(self,name,source):
		'''
		Generate a group for the file. Indent is implicitly none for this group
		'''
		return Group(name=name,source=source,indent='')
