import rollbar
import multiprocessing
from SlideRunner.dataAccess.slide import SlideReader
from PyQt5 import QtWidgets
from SlideRunner.gui import splashScreen
import sys

version = '1.99beta9'

rollbar.init('98503f735c5648f5ae21b6c18e04926a')
def main():
    try:
        multiprocessing.freeze_support()
        multiprocessing.set_start_method('spawn')
        slideReaderThread = SlideReader()
        slideReaderThread.start()
        app = QtWidgets.QApplication(sys.argv)
        splash = splashScreen.splashScreen(app, version)
        import SlideRunner.general.pluginFinder
        pluginList = SlideRunner.general.pluginFinder.pluginList
        from SlideRunner import SlideRunner
        SlideRunner.main(slideReaderThread=slideReaderThread, app=app, splash=splash, 
                         version=version, pluginList=pluginList)

    except Exception as e:
    	# catch-all
    	import traceback
    	print('Error: ',e)
    	traceback.print_exc()
    	rollbar.report_exc_info()
    	# equivalent to rollbar.report_exc_info(sys.exc_info())
    	print('An error has been reported to rollbar.')


if __name__ == '__main__':
	main()

