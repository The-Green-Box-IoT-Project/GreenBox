from . import generator

for module in [generator]:
    if hasattr(module, 'init'):
        module.init()