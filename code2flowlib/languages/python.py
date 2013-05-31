from code2flowlib.engine import *

indentPattern = re.compile(r"^( +|\t+)\S",re.MULTILINE)
def getIndent(colonPos,sourceString):
	try:
		return indentPattern.search(sourceString[colonPos:]).group(1)
	except:
		pdb.set_trace()





class SourceCode(SourceCode):
	blockComments = [
		{'start':'"','end':'"'}
		,{'start':"'",'end':"'"}
		,{'start':"'''",'end':"'''"}
		,{'start':'"""','end':'"""'}
		]
	inlineComments = "#"

	def getSourceInBlock(self,colonPos):
		indent = getIndent(colonPos,self.sourceString)

		endPos = colonPos

		lines = self.sourceString[colonPos:].split('\n')[1:]
		for line in lines:
			if line.startswith(indent) or line.strip()=='':
				endPos += len(line)+1 #+1 for the newlines lost
			else:
				break
		return self[colonPos+1:endPos] #+1 to start beyond colonPos


class Node(Node):
	sameScopeKeyword = 'self'

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

class Edge(Edge):
	pass

class Group(Group):

	classPattern = re.compile(r"^class\s(\w+)\s*(\(.*?\))?\s*\:",re.MULTILINE)
	#implicitName = 'module'

	def __init__(self,indent='',**kwargs):
		'''
		Expects name,indent,source, and optionally parent
		'''
		self.indent = indent

		super(Group,self).__init__(**kwargs)

		if not self.parent:
			indent = ''

		self.generateNodes()
		if not self.parent:
			self.generateSubgroups()
			self.nodes.append(self.generateImplicitNode())


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
			lineNumber = self.source.getLineNumber(colonPos)
			classGroup = Group(name=name,definitionString=definitionString,indent=indent,source=source,parent=self,lineNumber=lineNumber)
			self.subgroups.append(classGroup)


	def generateNewObjectPattern(self):
		return re.compile(r'%s\s*\('%self.name)

	def generateNewObjectAssignedPattern(self):
		return re.compile(r'(\w)\s*=\s*%s\s*\('%self.name)

	def generateImplicitNode(self):
		name = self.generateImplicitNodeName()
		source = self.generateImplicitNodeSource()
		return Node(name=name,definitionString=None,source=source,parent=self) #isImplicit=True

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

class Mapper(Mapper):

	def generateFileGroup(self,name,source):
		return Group(name=name,source=source,indent='')