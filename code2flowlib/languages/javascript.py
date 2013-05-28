
class Node(Node):
	sameScopeKeyword = 'this'

class Mapper(Mapper):
	blockComments = [{'start':"/*",'end':"*/"}]
	inlineComments = "//"

	functionPattern = re.compile(r"\Wfunction\s+(\w+)\s*\(.*?\)",re.MULTILINE|re.DOTALL)

	#methods are assigned to the object they are in
	methodPattern = re.compile(r"[^a-zA-Z0-9_\.]+(\w+)\s*(\:|\=)\s*function\s*\(",re.MULTILINE|re.DOTALL)

	#anonymous functions are called by functions and therefore assigned to them
	anonymousFunctionPattern = re.compile(r"\(\s*function\s*\(.*?\)",re.MULTILINE|re.DOTALL)

	#appendedMethodPatterd = re.compile(r"[^a-zA-Z0-9_\.]+(\w+)\.(\w+)\s*\=\s*function\s*",re.MULTILINE|re.DOTALL)



	#our internal representation. The entire javascript file will be in here
	fileAsString = ''

	def __init__(self,files):
		for f in files:
			with open(f) as fi:
				self.fileAsString += fi.read()

	def getLineNumber(self,pos):
		i=pos
		while True:
			try:
				return self.characterToLineMap[i]
			except KeyError:
				i-=1
			if not i:
				pdb.set_trace()

	def map(self):

		#Generate the file by removing comments
		self.fileAsString,self.characterToLineMap = self.removeComments(self.fileAsString)

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