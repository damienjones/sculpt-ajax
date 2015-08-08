# default settings

# set this to True to echo all AJAX requests/responses to
# the console
SCULPT_DUMP_AJAX = False

# if you want to use the standard error handlers, you will
# need to define the base directories for the message
# classes; 403, 404, and 500 especially rely on the "error"
# class

# The AjaxMessageView is versatile and accepts most of its
# configuration via parameters passed in urls.py. However,
# we often need to render a message (e.g. an error) from
# within the context of an existing request, without doing
# a redirect (which would destroy the HTTP response code)
# or trying to do some funky Django internal sub-request.
# That means the AjaxMessageView needs (at least for some
# subset of its uses) to be able to render responses without
# that configuration route. These values provide that
# configuration. You can still use urls.py for additional
# cases if you don't need to render them from within other
# requests.

# base template for HTML message; since this needs to
# reflect your site's overall appearance, you will likely
# want to override this with a reference to your own
# template, but you can use the existing one as a guide
SCULPT_AJAX_HTML_BASE_TEMPLATE_NAME = 'sculpt_ajax/html_message.html'

# base template for AJAX response; since this needs to be
# in the correct format for the client-side AJAX handler
# to recognize, you most likely will NOT need to customize
# this, but you can if you must
SCULPT_AJAX_AJAX_BASE_TEMPLATE_NAME = 'sculpt_ajax/ajax_message.html'

# base template path for categories
SCULPT_AJAX_TEMPLATE_BASE_PATH = 'sculpt_ajax'
