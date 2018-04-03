class pluginEntry:
    mainClass = None
    commonName = None
    plugin = None
    inQueue = None
    outQueue = None
    version = None
    receiverThread = None

    def __str__(self):
        return self.commonName