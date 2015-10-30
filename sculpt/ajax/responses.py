from django.http import JsonResponse
from django.template.loader import get_template, render_to_string
from django.utils.encoding import force_text
from sculpt.ajax import settings
import copy
import json

# we'd like to use the to_json method in
# sculpt.json_tools if it's available, but if it
# isn't, we define it as a no-op
try:
    from sculpt.json_tools import to_json
except ImportError:
    to_json = lambda x: x

#
# success-ish responses
#

# AJAX mixed response: one or more of results, modal, html, toast
#
# NOTE: if you only need one, it is probably easier to use one
# of the more specific types below; they are all wrappers around
# this class
#
# NOTE: validation here is cursory and mainly is intended to
# catch programming or configuration mistakes
#
class AjaxMixedResponse(JsonResponse):

    def __init__(self, **kwargs):
        # make sure we have at least one required key
        valid_response = False
        for k in [ 'results', 'modal', 'toast', 'html' ]:
            if k in kwargs:
                valid_response = True
                break
        if not valid_response:
            raise Exception('AJAX mixed response requested but no recognized response types provided')

        # validate each of our possible sub-keys and
        # make sure they're JSON-able

        if 'modal' in kwargs:
            modal = kwargs['modal']
            if 'code' not in modal or 'message' not in modal:
                raise Exception('AJAX modal response requested but code and message values are required')
                
            # JSON-safe the acceptable bits
            attrs = [ 'code', 'title', 'message' ]
            if 'size' in modal and modal['size'] != None:
                # NOTE: we ignore size if it's None as it confuses the JavaScript
                attrs.append('size')
            kwargs['modal'] = to_json(modal, attrs)

        if 'toast' in kwargs:
            toast_list = kwargs['toast']
            if isinstance(toast_list, dict):
                toast_list = [ toast_list ]     # a single dict is permitted, wrap as list
            for toast in toast_list:
                if 'duration' not in toast or 'html' not in toast:
                    raise Exception('AJAX toast response requested but a toast is missing required duration or message values')
                    
            kwargs['toast'] = to_json(toast_list)
            
        if 'html' in kwargs:
            html_list = kwargs['html']
            for html in html_list:
                if 'id' not in html or 'html' not in html:
                    raise Exception('AJAX HTML update response requested but an update is missing required id or html values')
                    
            kwargs['html'] = to_json(html_list)

        # NOTE: we don't apply to_json() to any "results"
        # data, as we assume this is done by the calling
        # code in order to control object serialization

        # this value is a marker to the client-side code
        # that indicates it adheres to the correct JSON
        # response format
        kwargs['sculpt'] = 'ajax'

        super(AjaxMixedResponse, self).__init__(kwargs)

    # a very, very common pattern is to create a toast
    # or modal response, accompanied by a batch of HTML
    # updates, but to have all of that data configured
    # in urls.py and even to have different responses
    # to the same request based on what happens in the
    # data (e.g. removing an item from the cart instead
    # of updating it because the quantity was set to
    # zero)
    #
    # to faciliate this, we provide this factory method
    # that produces a mixed response, rendering templates
    # with the given context data
    #
    # this expects a response_data dict with the
    # following keys (all optional):
    #
    #   modal               a dict:
    #       template_name a modal response
    #       title_template_name   modal's title template (optional)
    #       title           bare string for modal title (not template) (optional)
    #   toast               a dict or list of dicts:
    #       template_name   a toast response
    #       duration        how long to leave the toast up
    #   updates             a list:
    #       id              the HTML ID to be updated
    #       template_name   the template to render
    #       class_add       class(es) to add to the html_id object
    #       class_remove    class(es) to remove from the html_id object
    #
    # if a modal is returned, its code will be null
    #
    # As a convenience, you can disable the modal or
    # toast with an additional flag so you don't have
    # to clobber the response configuration in special
    # circumstances; this is especially important since
    # Django creates a view object for each request
    # but the config data would be shared among all
    # instances, so modifying them on the fly would
    # require deep-copying them first.
    #
    @classmethod
    def create(cls, context, response_data, show_modal = True, show_toast = True, show_updates = True):
        response = {}

        # do a modal
        if show_modal and 'modal' in response_data:
            modal_template = get_template(response_data['modal']['template_name'])
            modal_html = modal_template.render(context)
            if 'title' in response_data['modal']:
                modal_title = response_data['modal']['title']
            else:
                modal_title_template = get_template(response_data['modal']['title_template_name'])
                modal_title = modal_title_template.render(context)
            response['modal'] = {
                    'code': None,
                    'title': modal_title,
                    'message': modal_html,
                }
            if 'size' in response_data['modal']:
                response['modal']['size'] = response_data['modal']['size']

        # do toast
        if show_toast and 'toast' in response_data:
            response['toast'] = cls.render_toast(context, response_data['toast'])

        # do HTML updates
        if show_updates and 'updates' in response_data:
            response['html'] = cls.render_html_templates(context, response_data['updates'])

        # if we are given data results, pass those along
        # without modification
        if 'results' in response_data:
            response['results'] = response_data['results']
            
        # now create the response based on what we have
        return AjaxMixedResponse(**response)
        
    # In many AJAX requests you will need to render a set of
    # HTML fragments and return them as an AJAX HTML update
    # response. The IDs and template names need to come from
    # the urls.py but configuring individual variable names
    # for each one gets tiresome. This takes a list of
    # dicts describing an update, renders them, and returns
    # them as a list of {'id':id,'html':rendered_template}
    # items suitable for passing to the AjaxHTMLResponse
    # constructor. The dicts are the same format as the
    # returned data, except 'template_name' is given instead
    # of 'html'.
    #
    @classmethod
    def render_html_templates(cls, context, updates):
        rendered_html = copy.deepcopy(updates)
        for i in range(len(rendered_html)):
            # render the update                
            template_name = rendered_html[i].pop('template_name', None)     # removes it from the dict so it won't go client-side
            if template_name is not None:
                # None is interpreted to mean the HTML is already rendered
                template = get_template(template_name)
                rendered_html[i]['html'] = template.render(context)

        return rendered_html

    # sometimes we need to render toast, too
    @classmethod
    def render_toast(cls, context, toast_list):
        if isinstance(toast_list, dict):
            toast_list = [ toast_list ]
        rendered_toast_list = []
        for toast in toast_list:
            toast_template = get_template(toast['template_name'])
            toast_html = toast_template.render(context)
            rendered_toast = {
                    'duration': toast.get('duration', settings.SCULPT_AJAX_DEFAULT_TOAST_DURATION),
                    'html': toast_html,
                }
            if 'class_name' in toast:
                rendered_toast['class_name'] = toast['class_name']
            rendered_toast_list.append(rendered_toast)

        return rendered_toast_list


# AJAX success response
# for when you need success, but it's a no-op client side
# NOTE: this might be bad UX, consider toast!
#
class AjaxSuccessResponse(AjaxMixedResponse):

    def __init__(self):
        super(AjaxSuccessResponse, self).__init__(results = {})


# AJAX data response
#
class AjaxDataResponse(AjaxMixedResponse):

    def __init__(self, response):
        super(AjaxDataResponse, self).__init__(results = response)


# AJAX HTML update response
#
class AjaxHTMLResponse(AjaxMixedResponse):

    def __init__(self, response):
        super(AjaxHTMLResponse, self).__init__(html = response)


# AJAX toast response
#
class AjaxToastResponse(AjaxMixedResponse):

    def __init__(self, response, **kwargs):
        super(AjaxToastResponse, self).__init__(toast = response)


# AJAX modal response
#
class AjaxModalResponse(AjaxMixedResponse):

    def __init__(self, response = None, **kwargs):
        super(AjaxModalResponse, self).__init__(modal = response)


#
# error-ish responses
#

# AJAX redirect response
#
class AjaxRedirectResponse(JsonResponse):

    def __init__(self, response):
        super(AjaxRedirectResponse, self).__init__({ 'sculpt': 'ajax', 'location' : response })


# AJAX exception response
# NOTE: this is NOT an Exception, it's a response
#
class AjaxExceptionResponse(JsonResponse):

    def __init__(self, response = None, **kwargs):
        if not response:
            response = to_json(kwargs, [ 'code', 'title', 'message' ])
            if 'size' in kwargs:
                response['size'] = kwargs['size']
        # this really should verify the required keys are present in the response
        # (code, title, message)
        super(AjaxExceptionResponse, self).__init__({ 'sculpt': 'ajax', 'exception' : response })


# AJAX error response
# NOTE: this is NOT an Exception, it's a response
#
class AjaxErrorResponse(JsonResponse):

    def __init__(self, response = None, **kwargs):
        if not response:
            response = to_json(kwargs, [ 'code', 'title', 'message' ])
            if 'size' in kwargs:
                response['size'] = kwargs['size']
        # this really should verify the required keys are present in the response
        # (code, title, message)
        super(AjaxErrorResponse, self).__init__({ 'sculpt': 'ajax', 'error' : response })


# AJAX form error response
#
class AjaxFormErrorResponse(JsonResponse):

    def __init__(self, form, last_field = None, focus_field = None, error = None, context = None, updates = None, toast = None):
        # check whether this is a partial validation response
        is_partial = last_field != None
        
        # we shouldn't do this unless we actually have form errors;
        # that would be a programming mistake
        # NOTE: we'll accept a partial-validation error-free state
        if not is_partial and not form._errors:
            raise Exception('attempt to return form errors when there are none')

        # we need to format the errors in the form in a way that
        # is suitable for our AJAX handler on the client
        #
        # NOTE: Django's method is that the ValidationError and
        # ErrorList classes should "know" how to format themselves,
        # but they left very little in the way of ability to
        # intelligently override that. Instead, we act as though
        # errors are collected into a well-defined format, and
        # the layer that returns these errors to the client is
        # responsible for correctly formatting them.

        # we walk the error list in field declaration order
        error_list = []
        for name, field in form.fields.iteritems():
            if name in form._errors:
                field_error_list = []
                for message in form._errors[name]:
                    field_error_list.append(force_text(message))
                # use prefixed name so client side can find it
                error_list.append([ form.add_prefix(name), field.label, field_error_list ])

        # now append the global errors
        name = '__all__'
        if name in form._errors:
            field_error_list = []
            for message in form._errors[name]:
                field_error_list.append(force_text(message))
            error_list.append([ None, None, field_error_list ])

        # now that we have a formatted error list, return it
        results = {
                'sculpt': 'ajax', 
                'form_error': error_list,
            }
        if is_partial:
            results['partial'] = {
                    # these should ALREADY have prefixes on them
                    'last_field': last_field,
                    'focus_field': focus_field,
                }
        if error is not None:
            results['error'] = to_json(error, [ 'code', 'title', 'message' ])   # just these valid fields
            if 'size' in error:
                results['error']['size'] = error['size']
        if updates is not None:
            results['html'] = AjaxMixedResponse.render_html_templates(context, updates)
        if toast is not None:
            results['toast'] = AjaxMixedResponse.render_toast(context, toast)

        super(AjaxFormErrorResponse, self).__init__(results)


#
# RAW response
#

# Occasioanlly, a response will be generated
# that contains JSON data already serialized
# to a string. We want to preserve that output
# without re-encoding it, but we also do not
# want to rewrite all the JSON response stuff.
#
# This is good any time you're using templates
# to render JSON responses; you may also find
# the {% escapejs %} ... {% endescapejs %}
# tag helpful in writing the JSON.
#
class AjaxRawResponse(JsonResponse):

    def __init__(self, data, *args, **kwargs):

        # let the JSON class do its thing
        super(AjaxRawResponse, self).__init__({}, *args, **kwargs)

        # rewrite the response to be out data
        # without escaping
        self.content = data
