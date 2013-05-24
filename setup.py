from distutils.core import setup
setup(name='code2flow',
	version='0.1',
	description='Visualize your source code as DOT flowcharts',
	long_description=open('README.md').read(),
	scripts=['code2flow.py'],
	author='Scott Rogowski',
	author_email='scott@scottrogowski.com',
	url='https://github.com/scottrogowski/code2flow',
	packages=['distutils','distutils.command']
	)