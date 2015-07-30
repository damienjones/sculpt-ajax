"""A library for processing all forms via AJAX."""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
# with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
#     long_description = f.read()

setup(
	name='sculpt.ajax',
	version='0.1',
	description='A library for processing all forms via AJAX.',
	long_description='',
	url='https://github.com/damienjones/sculpt-ajax',
	author='Damien M. Jones',
	author_email='damien@codesculpture.com',
	license='LGPLv2',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
	], 
	keywords='',
	packages=find_packages(),
	install_requires=[
		'sculpt-common>=0.2',
	],
	# package_data={},
	# data_files=[],
	# entry_points={},
	# console_scripts={},
)
