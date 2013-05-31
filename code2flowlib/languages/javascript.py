from code2flowlib.engine import *

class Node(Node):
	sameScopeKeyword = 'this'

class Edge(Edge):
	pass

class SourceCode(SourceCode):
	blockComments = [
		{'start':'"','end':'"'}
		,{'start':"'",'end':"'"}
		,{'start':"/*",'end':"*/"}
		,{'start':re.compile(r'[\=\(]\s*\/[^/]'),'end':re.compile(r'[^\\]/')}
		]
	inlineComments = "//"

class Group(Group):
	REWORD = r"\(.*?\)(\w+[a-zA-Z])\W"
	REWORDPATH = r"\S+"

	REPARENTFUNCTION = r"\s+(\w+[a-zA-Z])\W"

	def __init__(self,isFunction=True,isAnon=False,**kwargs):
		'''
		With javascript, we want to get the functions and then determine what block they are in

		Or

		We could determine namespaces first and then functions. The problem is that it is difficult to determine what a block is in javascript

		Blocks could be like
		namespace = {
			func 1 =
			func 2 =
			}

		They could be functions in themselves like
		namespace = function() {
			func 1 =
			func 2 = function
			}

		So, we could search for function definitions and then seek downwards building the namespace as we go

		The problem is then, what is the difference between a group and a node in javascript?

		When it turns out that a node is a group, we can just put that node into the group? That would probably work

		Or, we could find all namespaces first and then determine which namespace a function is part of
		That would involve building a javascript ast probably
		function a() {}
		a = {}
		a = function() {}


		New way to do this???
		More like the python way at least and allows for multiple namespace levels


		Slice to [:firstOpenBracket]

		search end of slice for functions (can use $ regex)
			if found:
				Recursively create new functional group
		else search end of slice for objects
			Recursively create new group
		else
			pdbsettrace. There might be something else...

		if functiontype: (filegroup is a functiontype)
			create implicit node out of sliced

		trim those groups with no descendents and no nodes. They are simple objects and out of the scope of this project
		Those groups with only the implicit node will be deleted and the node will move to the parent group

		We could search for

		filegroup
		'''

		super(Group,self).__init__(**kwargs)
		self.isAnon = isAnon

		print
		print
		print self.source
		print self.name
		#pdb.set_trace()

		groupFrameSource = self.source[0:len(self.source.sourceString)]
		openBracket = groupFrameSource.find('{')

		while openBracket != -1:
			'''
			While we do have a block to handle:
			* find the close bracket for this block
			* extract the source of this block

			* update our groupFrameSource which we will use later to build the implicit node
			* generate the  new group

			find the next block to handle

			'''
			closeBracket = groupFrameSource.endDelimPos(openBracket+1)
			if closeBracket == -1:
				closeBracket = len(groupFrameSource) #TODO this is bad...
				#pdb.set_trace()
			#pdb.set_trace()

			preBlockSource = groupFrameSource[:openBracket]
			blockSource = groupFrameSource[openBracket+1:closeBracket]

			newGroup = self.newGroupFromSources(preBlockSource,blockSource)
			if newGroup and not (newGroup.isAnon and len(newGroup.nodes)==1 and newGroup.nodes[0].name==newGroup.name):
				self.subgroups.append(newGroup)
				postBlockSource = groupFrameSource[closeBracket:]
				groupFrameSource = preBlockSource[:-1*len(newGroup.definitionString)] + postBlockSource
				closeBracket = closeBracket-len(blockSource)-len(newGroup.definitionString)

			openBracket = groupFrameSource.find('{',closeBracket)

		if isFunction:
			#if not self.parent:
			#	pdb.set_trace()
			newNode = Node(name=self.name,source=groupFrameSource,definitionString=self.definitionString,parent=self,lineNumber=self.lineNumber)
			self.nodes.append(newNode)


	FUNCTION_PATTERNS = [
		re.compile(r".*?\Wfunction\s+(\w+)\s*\(.*?\)\s*\Z",re.DOTALL)
		,re.compile(r".*?[^a-zA-Z0-9_\.]+([\w\.]+)\s*[\:\=]\s*function\s*\(.*?\)\s*\Z",re.DOTALL) #\.
		]

	OBJECT_PATTERNS = [
		re.compile(r".*?\W(\w+)\s*\=\s*$",re.DOTALL)
		]

	ANON_OBJECT_PATTERN = re.compile(r".*?\(\s*$",re.DOTALL)

	ANON_FUNCTION_PATTERN = re.compile(r".*?\(\s*function\s*\(.*?\)\s*\Z",re.DOTALL)


	def newGroupFromSources(self,preBlockSource,blockSource):

		for pattern in self.FUNCTION_PATTERNS:
			newGroup = self.newGroupFromSourcesAndPattern(preBlockSource,blockSource,pattern,isFunction=True)
			if newGroup:
				return newGroup

		for pattern in self.OBJECT_PATTERNS:
			newGroup = self.newGroupFromSourcesAndPattern(preBlockSource,blockSource,pattern,isFunction=False)
			if newGroup:
				return newGroup

		#if self.ANON_OBJECT_PATTERN.match(preBlockSource.sourceString):
		newGroup = self.newGroupFromSourcesAndPattern(preBlockSource,blockSource,self.ANON_FUNCTION_PATTERN,isAnon=True)
		if newGroup:
			return newGroup


		#	return None
		print
		print
		print preBlockSource.sourceString[-100:]
		print 'what is this?'
		#pdb.set_trace()
		return None


	def newGroupFromSourcesAndPattern(self,preBlockSource,blockSource,pattern,isFunction=True,isAnon=False):
		lastBracket = preBlockSource.sourceString.rfind('}')
		if lastBracket == -1:
			lastBracket = 0
		match = pattern.match(preBlockSource.sourceString[lastBracket:])
		if match:
			if isAnon:
				name = "(anon)"
			else:
				name = match.group(1)
			definitionString = match.group(0)
			lineNumber = preBlockSource.getLineNumber(match.start(0)+lastBracket)
			print preBlockSource,name
			#pdb.set_trace()
			return Group(name=name,source=blockSource,definitionString=definitionString,parent=self,lineNumber=lineNumber,isFunction=isFunction,isAnon=isAnon)
		return None

	def trimGroups(self):
		print self.name,
		print map(lambda x:x.name,self.subgroups)
		#pdb.set_trace()
		savedSubgroups = []

		for group in self.subgroups:
			#if group.name =='MainMap':
			#	pdb.set_trace()
			group.trimGroups()
			if not group.subgroups:
				if not group.nodes:
					#self.subgroups.remove(group)
					continue
				if len(group.nodes)==1 and group.nodes[0].name == group.name:
					group.nodes[0].parent = self
					self.nodes.append(group.nodes[0])
					#self.subgroups.remove(group)
					continue
			savedSubgroups.append(group)
		self.subgroups = savedSubgroups



	def generateNewObjectPattern(self):
		return re.compile(r'new\s+%s\s*\('%self.name)

	def generateNewObjectAssignedPattern(self):
		return re.compile(r'(\w)\s*=\s*new\s+%s\s*\('%self.name)

	def generateNodes(self):
		'''
		for each match, generate the node
		'''
		functionPatterns = self.generateFunctionPatterns()
		for pattern in functionPatterns:
			matches = pattern.finditer(self.source.sourceString)
			for match in matches:
				node = self.generateNode(match)
				self.nodes.append(node)
				self.generateOrAppendToGroup(node)




	def generateOrAppendToGroup(self,node):
		openDelimPos = self.source.openDelimPos(node.characterPos)

		if self.source.sourceString[openDelimPos] == '{':
			#this is a regular function, generate the group
			group = self.generateGroup(openDelimPos,node)
		elif self.source.sourceString[openDelimPos] == '(':
			#declare as an anonymous function
			#the caller shall still be found by going one higher
			while self.source.sourceString[openDelimPos] == '(':
				openDelimPos = self.source.openDelimPos(openDelimPos-1)
		else:
			pdb.set_trace()
			print 'what is this?'
		#print self.source.sourceString[openDelimPos]
		#pdb.set_trace()



	#TODO return False was just to get past mootools errors
	def generateGroup(self,bracketPos,node):
		reversePool = self.source.sourceString[:bracketPos][::-1]
		#match = re.search(self.REWORD,reversePool)

		#if not match:
		#	return Node(validObj = False)

		anonReversePattern=re.compile(r"\s*\).*?\(\s*noitcnuf\s*\(")
		functionReversePattern=re.compile(r"\s*\).*?\(\s*(\w+)\s+noitcnuf")
		methodReversePattern=re.compile(r"\s*\).*?\(\s*noitcnuf\s*(?:\=|\:)\s*(\w+)")
		objectReversePattern=re.compile(r"\s*(?:\=|\:)\s*(\w+)")

		'''
		try:
			if match.group(1)=='prototype'[::-1]:
				match = re.search(self.REWORD,reversePool[match.end(1):])
			if match.group(1)=='function'[::-1]:
				match = re.search(self.REWORD,reversePool[match.end(1):])
		except:
			pdb.set_trace()
			return False

		try:
			name = match.group(1)[::-1]
		except:
			pdb.set_trace()
			return False
		'''

		pdb.set_trace()

		nodes = [node]
		start = bracketPos
		end = self.source.endDelimPos(start+1,'{','}')
		pdb.set_trace()

		print match.group(0)

		return Group(name=name,source=self.source[start:end],definitionString=match.group(0)[::-1])



class Mapper(Mapper):

	functionPattern = re.compile(r"\Wfunction\s+(\w+)\s*\(.*?\)\s*\{",re.MULTILINE|re.DOTALL)

	#methods are assigned to the object they are in
	methodPattern = re.compile(r"[^a-zA-Z0-9_\.]+(\w+)\s*(\:|\=)\s*function\s*\(.*?\)\s*\{",re.MULTILINE|re.DOTALL)

	#anonymous functions are called by functions and therefore assigned to them
	anonymousFunctionPattern = re.compile(r"\(\s*function\s*\(.*?\)",re.MULTILINE|re.DOTALL)

	#appendedMethodPatterd = re.compile(r"[^a-zA-Z0-9_\.]+(\w+)\.(\w+)\s*\=\s*function\s*",re.MULTILINE|re.DOTALL)

	def generateFileGroup(self,name,source):
		return Group(name=name,source=source,isFunction=True)
	'''
	def map(self):


		for baseObject in ('document','navigator'):
			groups.append(Group(baseObject))

		#Find all the defined global functions in the file
		functionMatches = self.functionPattern.finditer(self.fileAsString)

		#Create the node for each global function
		for functionMatch in functionMatches:
			nodes.append(self.generateNode(functionMatch,self.fileAsString))

		#Find all methods
		methodMatches = self.methodPattern.finditer(self.fileAsString)

		#Create the node for each matched method
		for methodMatch in methodMatches:
			node = self.generateNode(methodMatch,self.fileAsString)
			for group in groups:
				if group.insideGroup(methodMatch.start(1)):
					print 'inside group'
					group.addNode(node)
					matchedGroup = group
					break
			else:
				print 'new group'
				obp = openBracketPos(self.fileAsString,methodMatch.start(1))
				matchedGroup = self.generateGroup(obp,self.fileAsString,node)
				if matchedGroup and matchedGroup.validObj and matchedGroup.name not in map(lambda x: x.name,groups):
					groups.append(matchedGroup)
			if matchedGroup and matchedGroup.validObj:
				nodes.append(node)
				node.setGroup(matchedGroup)


		#Find all anonymous functions
		anonymousMatches = self.anonymousFunctionPattern.finditer(self.fileAsString)
		#pdb.set_trace()

		for anonMatch in anonymousMatches:
			#pdb.set_trace()
			node = self.generateNode(anonMatch,self.fileAsString,nodeType="anonymous")
			obp = openBracketPos(self.fileAsString,anonMatch.start(0))

			#if this is not the LAST open bracket position, let this go for now
			#it is not worth adding little anon functions from jquery
			#conceptually, these are not even part of the jquery functions but the larger encompassing function
			if openBracketPos(self.fileAsString,obp-1) > 0:
				continue

			reversePool = self.fileAsString[:obp][::-1]
			try:
				parentName = re.match(self.REWORD,reversePool).group(1)[::-1]
			except AttributeError:
				#this happens if we could not find a parent name. If we could not, then pass
				parentName = "(anonymous wrapped function)"


			#pdb.set_trace()
			parentNode = Node(name=parentName,content='',lineNumber=self.getLineNumber(obp))

			nodes.append(node)
			nodes.append(parentNode)
			#edges.append(Edge(parentNode,node))


		#TODO self.appendedMethodPattern
		self.generateEdges()
	'''