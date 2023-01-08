from setuptools import setup

from code2flow.engine import VERSION

url_base = 'https://github.com/scottrogowski/code2flow'
download_url = '%s/archive/code2flow-%s.tar.gz' % (url_base, VERSION)

setup(
    name='code2flow',
    version=VERSION,
    description='Visualize your source code as DOT flowcharts',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    entry_points={
        'console_scripts': ['code2flow=code2flow.engine:main'],
    },
    license='MIT',
    author='Scott Rogowski',
    author_email='scottmrogowski@gmail.com',
    url=url_base,
    download_url=download_url,
    packages=['code2flow'],
    python_requires='>=3.6',
    include_package_data=True,
    classifiers=[
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
