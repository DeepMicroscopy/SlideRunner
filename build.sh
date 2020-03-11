# Build script for Mac OS X 
#
# make sure you have an old version of opencv2, else it does not work.
# --> pip install --upgrade opencv-python==3.3.0.9


pyinstaller --windowed --onefile main_osx.spec

plutil -replace  LSBackgroundOnly -bool false dist/SlideRunner.app/Contents/Info.plist

hdiutil create -volname SlideRunner -srcfolder dist/SlideRunner.app -ov -format UDZO SlideRunner.dmg
