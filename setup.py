from setuptools import setup

from lib.engine import VERSION

url_base = 'https://github.com/scottrogowski/code2flow'
download_url = '%s/archive/fastmap-%s.tar.gz' % (url_base, VERSION)

setup(
    name='code2flow',
    version=VERSION,
    description='Visualize your source code as DOT flowcharts',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    scripts=['code2flow'],
    license='MIT',
    author='Scott Rogowski',
    author_email='scottmrogowski@gmail.com',
    url=url_base,
    download_url=download_url,
    packages=['lib'],
    package_dir={'code2flow': 'lib'},
    python_requires='>=3.6',
    classifiers=[
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
