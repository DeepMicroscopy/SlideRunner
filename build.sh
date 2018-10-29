# Build script for Mac OS X 
#
# make sure you have an old version of opencv2, else it does not work.
# --> pip install --upgrade opencv-python==3.3.0.9


pyinstaller --windowed --onefile main_osx.spec