from setuptools import setup, find_packages

setup(name='SlideRunner',
      version='1.7.1',
      description='SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images',
      url='http://github.com/maubreville/SlideRunner',
      author='Marc Aubreville',
      author_email='marc.aubreville@fau.de',
      license='GPL',
      packages=find_packages(),
      install_requires=[
          'PyQt5', 'openslide-python>=1.1.1', 'pyqt5>=5.5.0', 'opencv-python>=3.1.0',
          'matplotlib>=2.0.0', 'numpy>=1.13', 'matplotlib>=2.0.0'
      ],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      zip_safe=False)
