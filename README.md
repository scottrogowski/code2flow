![code2flow logo](https://raw.githubusercontent.com/scottrogowski/code2flow/master/assets/code2flowlogo.png)

![Version 2.3.0](https://img.shields.io/badge/version-2.3.0-brightgreen) ![Build passing](https://img.shields.io/badge/build-passing-brightgreen) ![Coverage 100%](https://img.shields.io/badge/coverage-100%25-brightgreen) ![License MIT](https://img.shields.io/badge/license-MIT-green])

Code2flow generates [call graphs](https://en.wikipedia.org/wiki/Call_graph) for dynamic programming language. Code2flow supports Python, Javascript, Ruby, and PHP.

The basic algorithm is simple:

1. Translate your source files into ASTs.
2. Find all function definitions.
3. Determine where those functions are called.
4. Connect the dots. 

Code2flow is useful for:
- Untangling spaghetti code.
- Identifying orphaned functions.
- Getting new developers up to speed.

Code2flow will provide a *pretty good estimate* of your project's structure. No algorithm can generate a perfect call graph for a [dynamic language](https://en.wikipedia.org/wiki/Dynamic_programming_language) - even less so if that language is [duck-typed](https://en.wikipedia.org/wiki/Duck_typing). See the known limitations in the section below.

*(Below: Code2flow running on itself (excl javascript, PHP, & Ruby for clarity))*

![code2flow running against itself](https://raw.githubusercontent.com/scottrogowski/code2flow/master/assets/code2flow_output.png)

Installation
------------

```bash
pip3 install code2flow
```

If you don't have it already, you will also need to install graphviz. Installation instructions can be found [here](https://graphviz.org/download/).

Usage
-----

To generate a DOT file run something like:

```bash
code2flow mypythonfile.py
```

Or, for javascript:

```bash
code2flow myjavascriptfile.js
```

You can also specify multiple files or import directories:

```bash
code2flow project/directory/source_a.js project/directory/source_b.js
```

```bash
code2flow project/directory/*.js
```

```bash
code2flow project/directory --language js
```

There are a ton of command line options, to see them all, run:

```bash
code2flow --help
```

How code2flow works
------------

Code2flow approximates the structure of projects in dynamic languages. It is *not possible* to generate a perfect callgraph for a dynamic language. 

Detailed algorithm:

1. Generate an AST of the source code
2. Recursively separate groups and nodes. Groups are files, modules, or classes. More precisely, groups are namespaces where functions live. Nodes are the functions themselves.
3. For all nodes, identify function calls in those nodes.
4. For all nodes, identify in-scope variables. Attempt to connect those variables to specific nodes and groups. This is where there is some ambiguity in the algorithm because it is possible to know the types of variables in dynamic languages. So, instead, heuristics must be used.
5. For all calls in all nodes, attempt to find a match from the in-scope variables. This will be an edge.
6. If a definitive match from in-scope variables cannot be found, attempt to find a single match from all other groups and nodes.
7. Trim orphaned nodes and groups.
8. Output results.

Why is it impossible to generate a perfect call graph?
----------------

Consider this toy example in Python
```python
def func_factory(param):
    if param < .5:
        return func_a
    else:
        return func_b

func = func_factory(important_variable)
func()
```

We have no way of knowing whether `func` will point to `func_a` or `func_b` until runtime. In practice, ambiguity like this is common and is present in most non-trivial applications.

Known limitations
-----------------

Code2flow is internally powered by ASTs. Most limitations stem from a token not being named what code2flow expects it to be named.

* All functions without definitions are skipped. This most often happens when a file is not included.
* Functions with identical names in different namespaces are (loudly) skipped. E.g. If you have two classes with identically named methods, code2flow cannot distinguish between these and skips them.
* Imported functions from outside of your project directory (including from standard libraries) which share names with your defined functions may not be handled correctly. Instead when you call the imported function, code2flow will link to your local functions. E.g. if you have a function "search()" and call, "import searcher; searcher.search()", code2flow may link (incorrectly) to your defined function.
* Anonymous or generated functions are skipped. This includes lambdas and factories.
* If a function is renamed, either explicitly or by being passed around as a parameter, it will be skipped.


How to contribute
-----------------------

1. **Open an issue**: Code2flow is not perfect and there is a lot that can be improved. If you find a problem parsing your source that you can identify with a simplified example, please open an issue.
2. **Create a PR**: Even better, if you have a fix for the issue you identified that passes unit tests, please open a PR. 
3. **Add a language**: While dense, each language implementation is between 250-400 lines of code including comments. If you want to implement another language, the existing implementations can be your guide.


License
-----------------------------

Code2flow is licensed under the MIT license.
Prior to the rewrite in April 2021, code2flow was licensed under LGPL. The last commit under that license was 24b2cb854c6a872ba6e17409fbddb6659bf64d4c. 
The April 2021 rewrite was substantial so it's probably reasonable to treat code2flow as completely MIT-licensed.


Acknowledgements
-----------------------------


* In mid-2021, Code2flow was rewritten and two new languages were added. This was prompted and financially supported by the [Sider Corporation](https://siderlabs.com/). 
* The code2flow pip name was graciouly transferred to this project from [Dheeraj Nair](https://github.com/Dheeraj1998). He was using it for his own (unrelated) [code2flow](https://github.com/Dheeraj1998/code2flow) project. 
* Many others have contributed through bug fixes, cleanups, and identifying issues. Thank you!!!


Unrelated projects
-----------------------

The name, "code2flow", has been used for several unrelated projects. Specifically, the domain, code2flow.com, has no association with this project. I've never heard anything from them and it doesn't appear like they use anything from here.


Feedback / Contact
-----------------------------

Please do email!
scottmrogowski@gmail.com


Feature Requests
----------------

Email me. At any time, I'm spread thin across a lot of projects so I will, unfortunately, turn down most requests. However, I am open to paid development for compelling features.
