from . import catalog_interface

for module in [catalog_interface]:
    if hasattr(module, 'init'):
        module.init()