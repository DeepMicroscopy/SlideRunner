from setuptools import setup, find_packages

setup(name='SlideRunner',
      version='1.7.2.4',
      description='SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images',
      url='http://github.com/maubreville/SlideRunner',
      author='Marc Aubreville',
      author_email='marc.aubreville@fau.de',
      license='GPL',
      packages=find_packages(),
      package_data={
        'SlideRunner': ['artwork/*.png', 'Slides.sqlite'],
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
