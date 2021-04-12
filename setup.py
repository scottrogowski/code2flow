from setuptools import setup, find_packages

setup(
    name='code2flow',
    version='0.3',
    description='Visualize your source code as DOT flowcharts',
    long_description=open('README.md').read(),
    scripts=['code2flow'],
    package_dir={'lib': 'lib'},
    license='MIT',
    author='Scott Rogowski',
    author_email='scottmrogowski@gmail.com',
    url='https://github.com/scottrogowski/code2flow',
    packages=find_packages(),
    classifiers=(
        'Natural Language :: English',
        'Programming Language :: Python',
    )
)
