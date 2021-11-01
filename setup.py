
from setuptools import setup

setup(name='pytides',
      description='Tidal analysis and prediction library.',
      version='0.0.7',
      author='Sam Cox',
      author_email='sam.cox@cantab.net',
      url='http://github.com/sam-cox/pytides',
      packages=['pytides'],
      install_requires=['numpy>=1.8','scipy>=1.0'],
      license='MIT')
