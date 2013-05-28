from ..engine import *

indentPattern = re.compile(r"^( +|\t+)\S",re.MULTILINE)
def getIndent(colonPos,sourceString):
	try:
		return indentPattern.search(sourceString[colonPos:]).group(1)
	except:
		pdb.set_trace()

def getSourceInScope(colonPos,source):
	indent = getIndent(colonPos,source.sourceString)

	endPos = colonPos

	lines = source.sourceString[colonPos:].split('\n')[1:]
	for line in lines:
		if line.startswith(indent) or line.strip()=='':
			endPos += len(line)+1 #+1 for the newlines lost
		else:
			break
	return source[colonPos+1:endPos] #+1 to start beyond colonPos




class SourceCode(SourceCode):
	blockComments = [{'start':"'''",'end':"'''"},{'start':'"""','end':'"""'}]
	inlineComments = "#"

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




class Group(Group):

	classPattern = re.compile(r"^class\s(\w+)\s*(\(.*?\))?\s*\:",re.MULTILINE)

	def __init__(self,indent='',**kwargs):
		'''
		Expects name,indent,source, and optionally parent
		'''
		super(Group,self).__init__(**kwargs)
		self.indent = indent
		self.generateNodes()
		if self.parent:
			pass
		else:
			indent = ''
			self.generateSubgroups()

	def generateNodes(self):
		'''
		Find all function definitions in this indent level, generate the nodes, and append them
		'''
		functionPattern = self.generateFunctionPattern(self.indent)
		functionMatches = functionPattern.finditer(self.source.sourceString)
		print self.name
		#pdb.set_trace()
		for functionMatch in functionMatches:
			node = self.generateNode(functionMatch)
			self.nodes.append(node)
		print '%d nodes'%len(self.nodes)

	def generateFunctionPattern(self,indent):
		'''
		Return the regex for function definition at this indent level
		'''
		indent = indent.replace(' ',r'\s').replace('	',r'\t')
		return re.compile(r"^%sdef\s(\w+)\s*\(.*?\)\s*\:"%indent,re.MULTILINE|re.DOTALL)

	def generateNode(self,reMatch):
		'''
		Using the name match, generate the name, source, and parent of this node
		'''
		name = reMatch.group(1)

		colonPos = reMatch.end(0)

		if DEBUG:
			print self.source
			print 'generating node b',name, self.source.getLineNumber(colonPos)

		source = getSourceInScope(colonPos,self.source)
		lineNumber = self.source.getLineNumber(colonPos)
		return Node(name=name,source=source,parent=self,lineNumber=lineNumber)

	def generateSubgroups(self):
		classMatches = self.classPattern.finditer(self.source.sourceString)
		for classMatch in classMatches:
			print 'classMatch'
			name = classMatch.group(1)
			print name
			colonPos = classMatch.end(0)
			indent = getIndent(colonPos=colonPos,sourceString=self.source.sourceString)
			source = getSourceInScope(colonPos=colonPos,source=self.source)
			lineNumber = self.source.getLineNumber(colonPos)
			classGroup = Group(name=name,indent=indent,source=source,parent=self,lineNumber=lineNumber)
			self.subgroups.append(classGroup)
		#	pdb.set_trace()

	def generateNewObjectPattern(self):
		return re.compile(r'%s\s*\('%self.name)

	def generateNewObjectAssignedPattern(self):
		return re.compile(r'(\w)\s*=\s*%s\s*\('%self.name)

class Mapper(Mapper):
	files = {}

	def __init__(self,files):
		for f in files:
			with open(f) as fi:
				self.files[f] = fi.read()

	def map(self):
		#for module in self.modules:
		#	self.modules[module],characterToLineMap = self.removeComments(self.modules[module])
		#get the filename and the fileString
		#only first file for now
		filename,fileString = self.files.items()[0]

		#remove .py from filename
		filename = self.cleanFilename(filename)

		globalNamespace = Group(name=filename,indent='',source=SourceCode(fileString))
		#globalNamespace.generateNodes()
		nodes = globalNamespace.allNodes()

		#nodepdb.set_trace()
		edges = generateEdges(nodes)

		return globalNamespace,nodes,edges