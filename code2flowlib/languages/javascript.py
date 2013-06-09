'''
All of these classes subclass engine.py classes

Functions that begin with an "_" are local and do not replace anything in engine.py
'''

from code2flowlib.engine import *

class Node(Node):
	sameScopeKeyword = 'this'

	def linksTo(self,other):
		#Can either line in local scope using 'this' keyword
		#Or can link in namespaced/global scope
		#window.any.namespace is exactly the same as any.namespace
		#TODO when a function is defined within another function, there is no need for self keyword

		#pdb.set_trace()

		#if they are part of the same namespace, we can use the self keyword
		if other.parent == self.parent:
			if any(map(lambda pattern: pattern.search(self.source.sourceString), other.sameScopePatterns)):
				return True

		#if other.name == 'c':
		#	pdb.set_trace()

		#Otherwise, they can always be linked by a shared namespace
		#must generate namespace here because we are trimming the groups AFTER init of the node
		if any(map(lambda pattern: pattern.search(self.source.sourceString), other.generateAnyScopePatterns())):
			return True

		return False

	def getNamespace(self):
		if self.parent.name != self.name:
			return self.parent.getNamespace()
		else:
			return self.parent.parent.getNamespace()


	def generateAnyScopePatterns(self):
		'''
		How you would call this node from any scope
		'''
		return super(Node,self).generateAnyScopePatterns()+[
			re.compile(r"(?:[^a-zA-Z0-9\.]|\A)window\.%s\s*\("%(self.getFullName()),re.MULTILINE|re.DOTALL)
			]

class Edge(Edge):
	pass


class Group(Group):
	globalFrameName = 'window'

	PATTERNS = [
		{'type':'function','pattern':re.compile(r".*?\W(function\s+(\w+)\s*\(.*?\)\s*\Z)",re.DOTALL)}
		,{'type':'function','pattern':re.compile(r".*?[^a-zA-Z0-9_\.]+(([\w\.]+)\s*[\:\=]\s*function\s*\(.*?\)\s*\Z)",re.DOTALL)}
		,{'type':'object','pattern':re.compile(r".*?\W(([\w\.]+)\s*\=\s*\Z)",re.DOTALL)}
		,{'type':'anonFunction','pattern':re.compile(r".*?\(\s*(function\s*\(.*?\)\s*\Z)",re.DOTALL)}
		]


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
			#This will fail if it is a function pattern we do not understand
			newGroup = self.newGroupFromBlock(openBracket,closeBracket)

			if newGroup:
				'''
				Append this new group to the proper namespace

				Either
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
			newNode = self.generateImplicitNode(blocksToRemove)
			self.nodes.append(newNode)



	def getNamespace(self):
		'''
		Returns the full string namespace of this group including this group's name

		'''
		if not self.parent:
			return ''
		else:
			ret = self.name
			if self.parent.getNamespace():
				ret = self.parent.getNamespace() + '.' + ret
			return ret

	def trimGroups(self):
		'''
		If a group has only the implicit node, make that into a node and trim it
		'''

		savedSubgroups = []

		for group in self.subgroups:
			group.trimGroups()
			if not group.subgroups:
				if not group.nodes:
					continue
				if len(group.nodes)==1 and group.nodes[0].name == group.name:
					group.nodes[0].parent = self
					self.nodes.append(group.nodes[0])
					continue
			savedSubgroups.append(group)
		self.subgroups = savedSubgroups

	def generateNewObjectPattern(self):
		return re.compile(r'new\s+%s\s*\('%self.name)

	def generateNewObjectAssignedPattern(self):
		return re.compile(r'(\w)\s*=\s*new\s+%s\s*\('%self.name)

	"""
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
	"""


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

	def generateImplicitNode(self,blocksToRemove):
		#Get source by subtracting all of the 'spoken for' blocks
		source = self.source.copy()

		for block in blocksToRemove:
			source -= block.fullSource

		#Depending on whether or not this is the file root (global frame)
		#, set a flag and the node name
		if self.parent:
			isFileRoot = False
			name = self.name
		else:
			isFileRoot = True
			name = self._generateRootNodeName(self.name.rsplit('/',1)[-1])


		#generate and append the node
		return Node(name=name,source=source,definitionString=self.definitionString,parent=self,lineNumber=self.lineNumber,isFileRoot=isFileRoot)#isImplicit=True

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

class SourceCode(SourceCode):
	blockComments = [
		{'start':'"','end':'"'}
		,{'start':"'",'end':"'"}
		,{'start':"/*",'end':"*/"}
		,{'start':re.compile(r'[\=\(]\s*\/[^/]'),'end':re.compile(r'[^\\]/')}
		]
	inlineComments = "//"


class Mapper(Mapper):
	def generateFileGroup(self,name,source):
		'''
		Generate a group for the file. This will be a function group (isFunction=True)
		A function group can possibly call other groups.
		'''
		return Group(name=name,source=source,fullSource=source,isFunction=True)
