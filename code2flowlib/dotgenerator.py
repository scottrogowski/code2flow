def writeDotFile(dotFile,nodes,edges,groups,hidelegend=False):
	'''
	Write the dot file
	'''
	with open(dotFile,'w') as outfile:
		outfile.write(generateDotFile(nodes,edges,groups,hidelegend))

def generateDotFile(nodes,edges,groups,hidelegend=False):
	'''
	Return the string for the entire dotfile
	To be appended:
	- A legend
	- Nodes
	- Edges
	- Groups
	'''
	ret = "digraph G {\n"
	ret +="concentrate = true;"
	if not hidelegend:
		ret += """
			subgraph legend{
			rank = min;
			label = "legend";
			Legend [shape=none, margin=0, label = <
				<table cellspacing="0" cellpadding="0" border="1"><tr><td>Code2flow Legend</td></tr><tr><td>
				<table cellspacing="0">
				<tr><td>Regular function</td><td width="50px"></td></tr>
				<tr><td>Trunk function (nothing calls this)</td><td bgcolor='coral'></td></tr>
				<tr><td>Leaf function (this calls nothing else)</td><td bgcolor='green'></td></tr>
				<tr><td>Function call which returns no value</td><td>&#8594;</td></tr>
				<tr><td>Function call returns some value</td><td><font color='blue'>&#8594;</font></td></tr>
				</table></td></tr></table>
				>];}"""
	for node in nodes:
		if str(node):
			ret += str(node)+';\n'
	for edge in edges:
		ret += str(edge)+';\n'
	#if False:
	for group in groups:
		ret += str(group)+';\n'

	ret += '}'

	return ret