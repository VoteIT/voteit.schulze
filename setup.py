import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'pyramid',
    'colander',
    'deform',
    'voteit.core',
    'python-vote-core',
    ]

setup(name='voteit.schulze',
      version='0.0',
      description='Schulze poll for VoteIT',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires = requires,
      tests_require= requires,
      test_suite="voteit.schulze",
      entry_points = """\
      """,
      message_extractors = { '.': [
              ('**.py',   'chameleon_python', None ),
              ('**.pt',   'chameleon_xml', None ),
              ]},
      
      )
