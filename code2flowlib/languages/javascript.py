from code2flowlib.engine import *

class Node(Node):
	sameScopeKeyword = 'this'


	#def __init__(self,**kwargs):
	#	super(Node,self).__init__()



	def linksTo(self,other):
		#Can either line in local scope using 'this' keyword
		#Or can link in namespaced/global scope
		#window.any.namespace is exactly the same as any.namespace
		#TODO when a function is defined within another function, there is no need for self keyword

		#if they are part of the same namespace, we can use the self keyword
		if other.parent == self.parent:
			if any(map(lambda pattern: pattern.search(self.source.sourceString), other.sameScopePatterns)):
				return True

		#if other.name == 'c':
		#	pdb.set_trace()

		#Otherwise, they can always be linked by a shared namespace
		#must generate namespace here because we are trimming the groups AFTER init of the node
		if any(map(lambda pattern: pattern.search(self.source.sourceString), other.generateNamespacePatterns())):
			return True

		return False

	def getNamespace(self):
		if self.parent.name != self.name:
			return self.parent.getNamespace()
		else:
			return self.parent.parent.getNamespace()


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
	globalFrameName = 'window'

	PATTERNS = [
		{'type':'function','pattern':re.compile(r".*?\W(function\s+(\w+)\s*\(.*?\)\s*\Z)",re.DOTALL)}
		,{'type':'function','pattern':re.compile(r".*?[^a-zA-Z0-9_\.]+(([\w\.]+)\s*[\:\=]\s*function\s*\(.*?\)\s*\Z)",re.DOTALL)}
		,{'type':'object','pattern':re.compile(r".*?\W(([\w\.]+)\s*\=\s*\Z)",re.DOTALL)}
		,{'type':'anonFunction','pattern':re.compile(r".*?\(\s*(function\s*\(.*?\)\s*\Z)",re.DOTALL)}
		]

	'''
	REWORD = r"\(.*?\)(\w+[a-zA-Z])\W"
	REWORDPATH = r"\S+"

	REPARENTFUNCTION = r"\s+(\w+[a-zA-Z])\W"
	ANON_OBJECT_PATTERN = re.compile(r".*?\(\s*$",re.DOTALL)
	'''

	def getNamespace(self):
		if not self.parent or self.isAnon:
			return ''
		else:
			namespace = self.parent.getNamespace()
			if namespace:
				return namespace+'.'+self.name
			else:
				return self.name


	def __init__(self,isFunction=True,isAnon=False,**kwargs):
		'''
		Generate a new group

		Iteratively find blocks (objects and functions delimited by brackets) within this group and generate subgroups from them
		If this is a functional group (can call functions and is not a simple array)
		, remove the subgroups found from the sourcecode and use those to generate the implicit node

		isFunction means the group is a regular function and has an implicit node
		not isFunction would mean the group is an object meant for grouping like a = {b=function,c=function}

		isAnon means the function has no name and is not likely to be called outside of this scope
		'''

		super(Group,self).__init__(**kwargs)
		self.isAnon = isAnon

		blocksToRemove = []

		openBracket = self.source.find('{')

		while openBracket != -1:
			'''
			While we do have a "next function/object" to handle:
			* find the close bracket for this block
			* extract the source of the block and the source immediately prior to this block
			* generate a group from this source and the prior source
			* if we managed to create a group, see below
			'''

			closeBracket = self.source.matchingBracketPos(openBracket)
			if closeBracket == -1:
				print "Could not find closing bracket for open bracket on line %d in file %s"%(self.source.getLineNumber(openBracket),self.name)
				print "You might have a syntax error. Setting closing bracket position to EOF"
				closeBracket = len(self.source)

			#Try generating a new group
			newGroup = self.newGroupFromBlock(openBracket,closeBracket)

			if newGroup:
				'''
				If we did manage to generate a group there are one of two options

				A. The new group was not anonymous, and contained more than an implicit node
				B. The new group was anonymous but had subgroups in which case we want those subgroups to be our subgroups

				Either way:
				1. push the newly created group to it's parent  which is probably us unless something like MainMap.blah = function happened
				2. append this group to the groups we will later have to remove when generating the implicit node
				'''
				if not (newGroup.isAnon and len(newGroup.nodes)==1 and newGroup.nodes[0].name==newGroup.name):
						newGroup.parent.subgroups.append(newGroup)
						blocksToRemove.append(newGroup)
				elif newGroup.subgroups:
					for group in newGroup.subgroups:
						if group.parent == newGroup:
							group.parent = self
						group.parent.subgroups.append(group)
					blocksToRemove.append(newGroup)

			#get the next block to handle
			openBracket = self.source.find('{',closeBracket)

		if isFunction:
			'''
			If this is a function, generate the implicit node for this group
			'''

			#Get source by subtracting all of the 'spoken for' blocks
			source = self.source.copy()

			for block in blocksToRemove:
				source -= block.fullSource

			#Depending on whether or not this is the file root (global frame)
			#, set a flag and the node name
			if self.parent:
				isFileRoot=False
				name = self.name
			else:
				isFileRoot=True
				name = self.generateRootNodeName(self.name.rsplit('/',1)[-1])


			#generate and append the node
			newNode = Node(name=name,source=source,definitionString=self.definitionString,parent=self,lineNumber=self.lineNumber,isFileRoot=isFileRoot)#isImplicit=True
			self.nodes.append(newNode)





	def newGroupFromBlock(self,openBracket,closeBracket):
		'''
		Using the sourcecode before the block, try generating a function using all of the patterns we know about
		If we can generate it, return a new group with the sourcecode within the block
		'''
		preBlockSource = self.source[:openBracket]
		blockSource = self.source[openBracket:closeBracket+1]

		for pattern in self.PATTERNS:
			newGroup = self.newGroupFromSourcesAndPattern(preBlockSource,blockSource,pattern)
			if newGroup:
				return newGroup

		if DEBUG:
			print "===================="
			print preBlockSource.sourceString[-100:]
			print 'what is this?'

		return None


	def generateNamespacePatterns(self):
		return [
			re.compile(r"(?:\W|\A)%s\s*\("%(self.getFullName()))
			,re.compile(r"(?:\W|\A)window\.%s\s*\("%(self.getFullName()))
			]

	def generateNamespaces(self):
		return [
			self.getNamespace()
			,'window.'+self.getNamespace() if self.getNamespace() else 'window'
			]


	def findNamespace(self,namespace,callingGroup=None):
		if any(map(lambda thisNamespace: thisNamespace==namespace, self.generateNamespaces())):
			return self
		else:
			for group in self.subgroups:
				if group!=callingGroup and group.findNamespace(namespace=namespace,callingGroup=self):
					return group
			if self.parent and self.parent != callingGroup:
				return self.parent.findNamespace(namespace=namespace,callingGroup=self)
			else:
				return False



	def newGroupFromSourcesAndPattern(self,preBlockSource,blockSource,pattern):
		'''
		Given a functionPattern to test for, sourcecode before the block, and sourcecode within the block,
		Try to generate a new group


		'''

		#We are looking for a function name
		#Start by limiting the search area to that inbetween the last closed bracket and here
		#Then, try to match the pattern
		lastBracket = preBlockSource.sourceString.rfind('}')
		if lastBracket == -1:
			lastBracket = 0
		match = pattern['pattern'].match(preBlockSource.sourceString[lastBracket:])

		#If we found a match, generate a group
		if match:
			#name the function
			if pattern['type']=='anonFunction':
				name = "(anon)"
			else:
				name = match.group(2)

			#determine what group to attach this to.
			#if there was a dot in the namespace, we might need to attach this to something other than the group it was defined within
			attachTo = self
			if '.' in name:
				namespace, name = name.rsplit('.',1)
				group = self.findNamespace(namespace,self)
				if group:
					attachTo = group

			#generate the definition and line number
			definitionString = match.group(1)
			lineNumber = preBlockSource.getLineNumber(match.start(1)+lastBracket)
			fullSource = preBlockSource[lastBracket+match.start(1):]+blockSource

			#finally, generate the group
			return Group(
				name=name
				,source=blockSource[1:-1] #source without the brackets
				,fullSource=fullSource
				,definitionString=definitionString
				,parent=attachTo
				,lineNumber=lineNumber
				,isFunction=pattern['type'] in ('function','anonFunction')
				,isAnon=pattern['type'] == 'anonFunction')

		return None

	def trimGroups(self):
		if DEBUG:
			print self.name,
			print map(lambda x:x.name,self.subgroups)

		savedSubgroups = []

		for group in self.subgroups:
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
			print 'what is this?'


	"""
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
			return False

		try:
			name = match.group(1)[::-1]
		except:
			return False
		'''


		nodes = [node]
		start = bracketPos
		end = self.source.matchingBracketPos(start)

		return Group(name=name,source=self.source[start:end],definitionString=match.group(0)[::-1])
	"""


class Mapper(Mapper):

	functionPattern = re.compile(r"\Wfunction\s+(\w+)\s*\(.*?\)\s*\{",re.MULTILINE|re.DOTALL)

	#methods are assigned to the object they are in
	methodPattern = re.compile(r"[^a-zA-Z0-9_\.]+(\w+)\s*(\:|\=)\s*function\s*\(.*?\)\s*\{",re.MULTILINE|re.DOTALL)

	#anonymous functions are called by functions and therefore assigned to them
	anonymousFunctionPattern = re.compile(r"\(\s*function\s*\(.*?\)",re.MULTILINE|re.DOTALL)

	#appendedMethodPatterd = re.compile(r"[^a-zA-Z0-9_\.]+(\w+)\.(\w+)\s*\=\s*function\s*",re.MULTILINE|re.DOTALL)

	def generateFileGroup(self,name,source):
		'''
		OVERWRITES PARENT

		Generate a group for the file. This will be a function group (isFunction=True)
		A function group can possibly call other groups.
		'''
		return Group(name=name,source=source,fullSource=source,isFunction=True)
