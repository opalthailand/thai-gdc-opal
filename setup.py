from setuptools import setup, find_packages

setup(
    name='ckanext-cdp',
    version='0.1',
    description="CKAN Extension - CDP Integration",
    long_description="""
    CKAN extension to push resource data to CDP.
    """,
    classifiers=[],
    keywords='',
    author='Your Name',
    author_email='your.email@example.com',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.cdp'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests' #  For making HTTP requests
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