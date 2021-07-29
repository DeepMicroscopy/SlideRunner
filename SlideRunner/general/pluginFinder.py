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

sliderunner_plugins={}

for finder, name, ispkg in sorted(iter_namespace(SlideRunner.plugins)):
    try:
        mod = importlib.import_module(name)
        sliderunner_plugins[name] = mod
    except Exception as e:
        print('+++ Unable to active plugin: '+name,e)
        pass


pluginList = list()
shortNames=[]

for plugin in sorted(sliderunner_plugins.keys()):
    newPlugin = pluginEntry()
    classes = inspect.getmembers(sliderunner_plugins[plugin], inspect.isclass)
    for classIdx in range(len(classes)):
        if (classes[classIdx][0] == 'Plugin'):
            newPlugin = classes[classIdx][1]
            if newPlugin.shortName in shortNames:
                print('++++ ERROR: Plugin has duplicate short name: ',newPlugin.shortName)
                continue
            pluginList.append(newPlugin)


print('List of available plugins:')
for entry in pluginList:
    print('%20s   Version %s' % (entry.shortName, entry.version))

