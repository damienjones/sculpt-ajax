# default settings

# set this to True to echo all AJAX requests/responses to
# the console; you should probably turn this off for
# production configurations as it's both noisy and has
# sensitive data, but it's useful for development and
# at least safe in production if the console (and log file)
# are secured
SCULPT_AJAX_DUMP_REQUESTS = False

# When processing forms we want to keep all the actual
# error messages in a centralized file to make them easier
# to find, but we also need to be able to override and
# extend the error messages with app-specific ones.
# This list should be redefined in settings.py to include
# the app's error messages file in addition to the core
# sculpt-ajax one.
SCULPT_AJAX_FORM_ERROR_MESSAGES = (
        'sculpt.ajax.form_errors',
    )

# if the sculpt.model_tools is available, this can be
# set to True to derive all AjaxView classes in a way
# that includes AjaxLoginRequiredMixin
SCULPT_AJAX_LOGIN_REQUIRED = False

# toast messages need a default duration, in seconds
SCULPT_AJAX_DEFAULT_TOAST_DURATION = 4

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
