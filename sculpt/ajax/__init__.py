# functions and views for supporting AJAX requests and responses
#
# this is a high-level package that exports most symbols from
# sub-modules; see those packages for implementation details

# AJAX is pretty simple. Requests look like ordinary HTTP requests
# (and must be validated the same way) but the response needs the
# correct MIME type, and the body is just JSON data, XML, or HTML.
#
# On the browser side, though, there are a couple of wrinkles.
# If the server returns a redirect response, it won't reload the
# host page in the browser, it will just cause the browser to
# re-issue the AJAX request to the redirected URL. Also, we would
# like to be able to return error messages that could be presented
# in modal dialogs, rather than forcing the host page to be
# redirected to an error page (thus potentially losing state).
#
# We therefore define some standards around how WE will be doing
# AJAX:
#
# 1. All AJAX requests are POST requests.
#
#    AJAX allows GET but the browser will cache responses. This
#    is only appropriate if we are absolutely, positively sure
#    the request will never, ever fail. And since we're not really
#    going to be that sure, we should always preserve our ability
#    to process errors in an intelligent fashion.
#
# 2. All AJAX responses will be JSON, not HTML or XML.
#
#    If we return raw HTML, we have to try to guess when errors
#    happen and how to present them to the user. Also, the server
#    would have to know the context of the request in order to
#    format such an error in a way that makes sense. Skip it;
#    return HTML responses in a JSON wrapper (see below) so that
#    errors can be handled the same way for all AJAX calls.
#
# 3. All AJAX responses will adhere to a common format.
#
#    {
#        # mark this as a properly-formatted response
#        'sculpt': 'ajax',
#
#        # mutually-exclusive error-ish responses
#        'location': <url>,
#        'exception': {
#            'code': <error_code>,
#            'title': <error_title>,    # optional
#            'message': <error_message>
#        },
#        'error': {
#            'code': <error_code>,
#            'title': <error_title>,    # optional
#            'message': <error_message>
#        },
#        'form_error': [
#            [ <field_name>, <field_label>, [ <error_message>, ... ] ],
#            ...
#        ],
#
#        # non-exclusive success-ish responses
#        'results': <app-specific data>
#        'modal': {
#            'code': <error_code>,
#            'title': <error_title>,    # optional
#            'message': <error_message>
#        },
#        'toast': [
#            {
#                'duration': <time_in_milliseconds>,
#                'class_name': <css_class>,
#                'message': <toast_message>,
#                'delay': <delay>       # optional
#            },
#            ...
#        ],
#        'html': [
#            {
#                'id': <DOM_node_id>,
#                'html': <replacement_html>,
#                'class_add': <classes_to_add_to_DOM_node>,         # optional
#                'class_remove': <classesto_remove_from_DOM_node>   # optional
#            },
#            ...
#        ],
#    }
#
#    For error-ish responses, only ONE of the top-level keys
#    (location, exception, error, form_error) will be present.
#    For success-ish responses, at least one (but possibly more)
#    of the top-level keys is required. For details, see the
#    client-side code in sculpt_ajax.js.
#
#    NOTE: ALL formatted responses are returned with HTTP status
#    200 (OK), including errors. Other errors will be interpreted
#    by the JavaScript AJAX handler as hard server errors and
#    generate a canned response.
#
#    NOTE: we extract exceptions as a different type because they
#    indicate a problem with the server code, and they're handled
#    differently on the client side (styled).
#
# 4. Forms will always be submitted via AJAX.
#
#    The normal pattern is for a GET request to a form page to
#    return an empty (or perhaps pre-populated) form, and the POST
#    request to be the submission of that form data; successful
#    POST returns a redirect to the next page, and a failed POST
#    returns HTML with form errors embedded.
#
#    Instead, we want the POST form submission to happen via AJAX
#    so that we can return a lighter-weight JSON blob of errors
#    that can then be used to do some dynamic error highlighting.
#    We could certainly submit the data in a non-AJAX form, but
#    that makes the resulting display of errors take longer because
#    we're not just sending the error data, but the whole page
#    around it. That's not a great user experience, so we submit
#    via AJAX and return lighter-weight data.
#
#    This means that for form handlers, GET returns the regular
#    HTML and is not an AJAX request, but POST returns JSON data
#    because it IS an AJAX request.
