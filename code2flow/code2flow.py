#!/usr/bin/python
'''
Usage:
javascript2dot.py file.js
Then, with graphviz, open out.gv

* Green means leaf function (the function calls no other functions)
* Brown means trunk function (the function is called by no other function)
* Inverted arrow means that the called function returns something (it might just be a boolean though)

4/19 TODO:
We want to add labels to functions because the names must be different otherwise they break graphviz

Tokenize all functions by searching for the function keyword
Can be:
function a()
a = function()
a:function()

Can also attach functions via
s.a = function()

Or can have anonymous functions which will be connected to whereever

Determine their namespace immediately (only need to go one deep for now)
0

Group is the namespace
group will contain function nodes and possibly subgroups
There will be one global group to hold everything
In javascript, this is the window namespace which is also implicit
it must hold all of the nodes in its space
we will loop through the group to calculate edges and this will be a convenient way to determine namespace of the edges
They must maintain an internal representation of content for determining edges. Even subgroups should contain this. It makes things easier

Nodes are functions
node will contain a parent pointer to the namespace
Should also have an internal filestring of the content

With content, we must pass along objects with filestrings


'''
from src.engine import *

SUPPORTED_LANGUAGES = ['.js','.py']

if __name__ == "__main__":
	cli = argparse.ArgumentParser(description="See DOT graphs of your source code\nThis script is useful for documentation and code refactoring in simple projects")
	cli.add_argument('files', metavar='file(s)', nargs='+',help='the files or directory you are trying to graph')
	cli.add_argument('--outfile','-o', dest='outfile',help='where to write the resulting dotfile (should be .gv)',default='out.dot')
	cli.add_argument('--verbose','-v',action='store_true')
	cli.add_argument('--version', action='version', version='%(prog)s 0.1')

	args = cli.parse_args()

	#get all of the files in one list
	filetype = None
	files = []
	def handleFile(fileString):
		global filetype
		global files

		#set the filetype if not set
		if not filetype:
			filetype = fileString[fileString.rfind('.'):]
			if filetype not in SUPPORTED_LANGUAGES:
				raise Exception("File not supported")

		#if the file is part of the filetype we are using, append it
		if fileString[-1*len(filetype):]==filetype:
			files.append(fileString)

	#loop through arguments appending all files to the list
	for fil in args.files:
		if os.path.isfile(fil):
			handleFile(fil)
		elif os.path.isdir(fil):
			for fi in os.listdir(fil):
				handleFile(fil)

	#pull in the correct code which will superclass a lot of functions
	if filetype == '.js':
		from src.languages.javascript import *
	elif filetype == '.py':
		from src.languages.python import *

	mapper = Mapper(files)

	#do the mapping
	#(the globalNamespace and edges are global vars)
	globalNamespace,nodes,edges = mapper.map()

	#write the output dot file
	with open(args.outfile,'w') as outfile:
		outfile.write("digraph G {\n")
		outfile.write("""
			subgraph legend{
			rank = min;
			label = "legend";
			Legend [shape=none, margin=0, label = <
				<table cellspacing="0" cellpadding="0" border="1"><tr><td>CodeMapper Legend</td></tr><tr><td>
				<table cellspacing="0">
				<tr><td>Regular function</td><td width="50px"></td></tr>
				<tr><td>Trunk function (nothing calls this)</td><td bgcolor='red'></td></tr>
				<tr><td>Leaf function (this calls nothing else)</td><td bgcolor='green'></td></tr>
				<tr><td>Function call which returns no value</td><td>&#8594;</td></tr>
				<tr><td>Function call returns some value</td><td><font color='blue'>&#8594;</font></td></tr>
				</table></td></tr></table>
				>];}""")
		for node in nodes:
			if str(node):
				outfile.write(str(node)+';\n')
		for edge in edges:
			outfile.write(str(edge)+';\n')
		#pdb.set_trace()
		outfile.write(str(globalNamespace)+';\n')

		outfile.write('}')
	print "Completed the flowchart"
	print "To see it, run "

	#open it in graphvizif we are on os.x
	#if sys.platform == 'darwin':
		#os.system("open out.gv")
