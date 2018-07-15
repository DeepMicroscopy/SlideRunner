import SlideRunner.plugins
import pkgutil
import importlib
import inspect

from SlideRunner.general.types import pluginEntry

def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")

sliderunner_plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in sorted(iter_namespace(SlideRunner.plugins))
}

pluginList = list()

for plugin in sorted(sliderunner_plugins.keys()):
    newPlugin = pluginEntry()
    classes = inspect.getmembers(sliderunner_plugins[plugin], inspect.isclass)
    for classIdx in range(len(classes)):
        if (classes[classIdx][0] == 'Plugin'):
            newPlugin.mainClass = classes[classIdx][0]
            newPlugin.commonName = classes[classIdx][1].shortName
            newPlugin.plugin = classes[classIdx][1]
            newPlugin.inQueue = classes[classIdx][1].inQueue
            newPlugin.outQueue = classes[classIdx][1].outQueue
            newPlugin.version = classes[classIdx][1].version
        #    newPlugin.instance = classes[0][1]()
            pluginList.append(newPlugin)


print('List of available plugins:')
for entry in pluginList:
    print('%20s   Version %s' % (entry.commonName, entry.version))

