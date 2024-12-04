from setuptools import setup, find_packages
import sys, os
version = '0.1'
setup(
	name='ckanext-linenotify',
	version=version,
	description="LINE Notify plugin",
	long_description="""\
	""",
	classifiers=[],
	keywords='',
	author='Your Name',  # Update this
	author_email='your.email@example.com',  # Update this
	url='',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.linenotify'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
        'requests'
	],
	entry_points=\
	"""
        [ckan.plugins]
	linenotify=ckanext.linenotify.plugin:LINENotifyPlugin
	""",
)