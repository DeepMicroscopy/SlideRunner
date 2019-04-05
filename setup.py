from setuptools import setup, find_packages

# setup.py
import os
import sys

version = '1.20.0'

if sys.argv[-1] == 'publish':
  if (os.system("python setup.py test") == 0):
          if (os.system("python setup.py sdist upload") == 0):
              if (os.system("python setup.py bdist_wheel upload") == 0):
                 os.system("git tag -a %s -m 'version %s'" % (version, version))
                 os.system("git push")
    
  sys.exit()

# Below this point is the rest of the setup() function

setup(name='SlideRunner',
      version=version,
      description='SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images',
      url='http://github.com/maubreville/SlideRunner',
      author='Marc Aubreville',
      author_email='marc.aubreville@fau.de',
      license='GPL',
      packages=find_packages(),
      package_data={
        'SlideRunner': ['artwork/*.png', 'Slides.sqlite', 'plugins/*.py'],
      }, 
      install_requires=[
          'PyQt5', 'openslide-python>=1.1.1', 'pyqt5>=5.5.0', 'opencv-python>=3.1.0',
          'matplotlib>=2.0.0', 'numpy>=1.13', 'matplotlib>=2.0.0'
      ],
      setup_requires=['pytest-runner'],
      entry_points={
#            'console_scripts': [
#                'foo = my_package.some_module:main_func',
#                'bar = other_module:some_func',
#            ],
            'gui_scripts': [
                'sliderunner = SlideRunner.SlideRunner:main',
            ]
        },
      tests_require=['pytest'],
      zip_safe=False)
