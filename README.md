### Updates from April 2021
- I've entered into a contract with a generous sponsor to update code2flow. Expect a new version sometime in May of 2021.
- The new version will support Python3, ECMAScript 2018, PHP8, & Ruby3
- Most of the project will be rewritten and licensed under the MIT license. As always, existing code never changes license.
- The domain, code2flow.com is unrelated to this project and as far as I can tell through the internet archive, they launched their service after this repository was created. I've never heard anything from them and it doesn't appear like they use anything from here.
- The pip install, code2flow, has been claimed by a different unrelated project. For now, *don't install* code2flow from pip. Instead, scroll to the installation section for instructions.

code2flow
=========

Code2flow generate DOT flowcharts from your Python and Javascript projects

The algorithm is simple:

1. Find function definitions in your project's source code.
2. Determine where those functions are called.
3. Connect the dots. 

The result is a flowchart which approximates the functional structure of your program. In other words, *code2flow generates callgraphs*.

Code2flow is useful for:
- Untangling spaghetti code.
- Identifying orphaned functions
- Getting new developers up to speed.

Code2flow is EXPERIMENTAL and will provide a **rough overview** of the structure of simpler projects. There are many known limitations (see below).

Here is what happens when you run it on jquery
![Alt text](jqueryexample.png)

On the python calendar module
![Alt text](calendarexample.png)

On code2flow/languages/python.py
![Alt text](pythonexample.png)

Installation
------------

[Download](https://github.com/scottrogowski/code2flow/archive/master.zip), navigate to the directory, and run:

```bash
python setup.py install
```

If you don't have it already, you will also need to install graphviz. Installation instructions can be found [here](https://graphviz.org/download/).

Usage
-----

To generate a DOT file run something like:

```bash
code2flow mypythonfile.py
```

Or, for javascript

```bash
code2flow myjavascriptfile.js
```

You can also specify multiple files or import directories

```bash
code2flow project/directory/source_a.js project/directory/source_b.js
```

```bash
code2flow project/directory/*.js
```

```bash
code2flow project/directory --language js
```

There are a ton of command line options, to see them all, run

```bash
code2flow --help
```


Limitations
-----------

Code2flow approximates the structure of simple projects. Fundamentally, it works by using regular expressions - not abstract syntax trees. Therefore, it has many known limitations:

* All functions without definitions are skipped.
* Functions with identical names in different namespaces are (loudly) skipped. E.g. If you have two classes with methods, "add_element()", code2flow cannot distinguish between these and skips them.
* Imported functions from outside of your project directory (including from the standard library) which share names with your defined functions will not be handled correctly. Instead when you call the imported function, code2flow will link to your local functions. E.g. if you have a function "search()" and call, "import re; re.search()", code2flow links (incorrectly) to your defined function.
* Anonymous or generated functions are skipped.
* Renamed functions are not handled.
* Etc.

Think of Code2Flow as a starting point rather than a magic wand. After code2flow generates your flowchart, you probably need to spend some time cleaning up the output using a dot file editor. For a list of editors, look [here](https://graphviz.org/resources/).

License
-----------------------------

Code2flow is licensed under the MIT license.
Prior to the rewrite in April 2021, code2flow was licensed under LGPL. The last commit under that license was 24b2cb854c6a872ba6e17409fbddb6659bf64d4c. 
The April 2021 rewrite was substantial so it's probably reasonable to treat code2flow as completely MIT-licensed.


Feedback / Bugs / Contact
-----------------------------

Please do email!
scottmrogowski@gmail.com


How to contribute
-----------------------

1. You can contribute code! Code2flow has its limitations. Attempts to address these limitation would probably be helpful and accepted. New languages are especially appreciated!

2. You can spread the word! A simple way to help is to share this project with others. If you have a blog, mention code2flow! Linking from relevant questions on StackOverflow or other programming forums also helps quite a bit. I would do it myself but it is unfortunately against the community guidelines. The more exposure this project gets, the more I can devote my time to building it!


Feature / Language Requests
----------------

Email me. I am an independent contractor and can be convinced to work on this for an appropriate amount of money.
