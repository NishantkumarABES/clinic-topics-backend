import os
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

if ENVIRONMENT == 'development':
    from config.settings.dev import *
elif ENVIRONMENT == 'Production':
    from config.settings.prod import *
elif ENVIRONMENT == 'render':
    from config.settings.render import *
else:
    from config.settings.prod import *