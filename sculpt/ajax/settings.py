# merge default module settings with
# Django app's overrides

# start with our defaults
from sculpt.ajax.default_settings import *

# overlay Django app's settings; it's not
# a module that we can import directly, so
# import it and then overlay it into our
# global namespace
from django.conf import settings

for s in dir(settings):
    if s == s.upper():
        globals()[s] = getattr(settings, s)

# ...and that's it
