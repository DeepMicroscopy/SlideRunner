import rollbar

rollbar.init('98503f735c5648f5ae21b6c18e04926a')
try:
    from SlideRunner import SlideRunner

    SlideRunner.main()
except:
    # catch-all
    rollbar.report_exc_info()
    # equivalent to rollbar.report_exc_info(sys.exc_info())
    print('An error has been reported to rollbar.')

