from setuptools import setup, find_packages

setup(
    name='ckanext-cdp',
    version='0.1',
    description="CDP Extension for CKAN",
    long_description="",
    classifiers=[],
    keywords='',
    author='',
    author_email='',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.cdp'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests'  # Add requests to install_requires
    ],
    entry_points='''
        [ckan.plugins]
        cdp=ckanext.cdp.plugin:CDPPlugin
        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan
    ''',
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)