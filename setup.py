from setuptools import setup, find_packages
from toxmail import __version__


install_requires = ['PyTox', 'tornado', 'bonzo', 'pyzmail',
                    'pynacl']

try:
    import argparse     # NOQA
except ImportError:
    install_requires.append('argparse')


with open('README.rst') as f:
    README = f.read()


classifiers = ["Programming Language :: Python",
               "License :: OSI Approved :: Apache Software License",
               "Development Status :: 1 - Planning"]


setup(name='toxmail',
      version=__version__,
      packages=find_packages(),
      description=("Tox SMTP bridge"),
      long_description=README,
      license='APLv2',
      author="Tarek Ziade",
      author_email="tarek@ziade.org",
      include_package_data=True,
      zip_safe=False,
      classifiers=classifiers,
      install_requires=install_requires,
      entry_points="""
      [console_scripts]
      toxmail = toxmail.run:main
      """)
