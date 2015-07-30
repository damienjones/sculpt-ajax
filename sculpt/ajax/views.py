from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import RequestContext, Context
from django.template.loader import get_template, render_to_string
from django.views.generic import View

from sculpt.ajax.forms import AjaxFormAliasMixin
from sculpt.ajax.responses import AjaxSuccessResponse, AjaxHTMLResponse, AjaxModalResponse, AjaxRedirectResponse, AjaxMixedResponse, AjaxErrorResponse, AjaxExceptionResponse, AjaxFormErrorResponse

from collections import OrderedDict

base_view_class = View
if settings.SCULPT_AJAX_LOGIN_REQUIRED:
    from sculpt.model_tools.view_mixins import AjaxLoginRequiredMixin

    class AjaxViewBase(AjaxLoginRequiredMixin, View):
        pass

    base_view_class = AjaxViewBase

#
# views
#

# an AJAX view base class
#
# NOTE: this derives from View, not TemplateView, because the
# default implementation for GET handling MUST be to return
# an HTTP 405 (method not supported) rather than by default
# rendering a page. If we derived from TemplateView, the GET
# method would be handled automatically, but would raise a
# different exception when invoked that would return a 500
# Server Error response instead of 405. This class is suitable
# for a request which returns any of our standard AJAX
# responses only. For a form, which renders HTML on GET and JSON
# results on POST, please use AjaxFormView instead.
#
class AjaxView(base_view_class):

    # by default, we do not implement GET
    
    # POST handler will be implemented by the derived view class

    # which methods we should catch exceptions for and re-wrap
    # in AJAX-friendly wrappers; by default this is just POST,
    # but if your class is returning JSON responses for other
    # methods you should list them here so that errors are
    # shown instead of blowing up client-side code
    wrap_exceptions_methods = [ 'POST' ]

    # special handling: if an exception occurs in an AJAX POST, we
    # DO NOT want to return an exception as Django's default HTML-
    # formatted response. Instead, catch the exception and return
    # an AJAX-formatted error. However, we can't do this in a POST
    # handler because the derived class gets first crack at handling
    # it, and that's the code we need to wrap in try/except. So we
    # do the wrapping here, in dispatch.
    def dispatch(self, request, *args, **kwargs):

        # non-POST requests are not wrapped; you're on your own
        # for error handling as we assume a GET request is for the
        # form HTML
        if request.method not in self.wrap_exceptions_methods:
            return super(AjaxView, self).dispatch(request, *args, **kwargs)
            
        # otherwise it's a post (or at least something we're
        # supposed to wrap); trap exceptions
        try:
            # spew some debug data, perhaps
            if settings.SCULPT_DUMP_AJAX:
                raw_uri = request.META['RAW_URI'] if 'RAW_URI' in request.META else request.META['PATH_INFO']
                if request.META.get('CONTENT_TYPE') == 'multipart/form-data':
                    # Django has already parsed the body and dumping a
                    # full uploaded file's data will not be helpful
                    print 'AJAX request:', raw_uri, 'MULTIPART: <file upload> +', request.POST
                else:
                    # we'd like to print the raw request if we can
                    if hasattr(request, '_body'):
                        print 'AJAX request:', raw_uri, 'BODY:', request._body
                    else:
                        print 'AJAX request:', raw_uri, 'POST', request.POST

            # call the actual POST handler
            results = super(AjaxView, self).dispatch(request, *args, **kwargs)

            if not isinstance(results, JsonResponse):
                # we want to make sure all AjaxView handlers return
                # a response in the correct form; if not, we want
                # to trap those errors early in development rather
                # than let them skate by
                #
                # NOTE: we return this rather than raise it, because
                # we don't have a backtrace (it's not helpful) and
                # because it's already formatted as an error response
                #
                response = { 'code': 1, 'title': 'Invalid Response Type', 'message': 'Request generated an invalid response type (%s)' % results.__class__.__name__ }
                if settings.SCULPT_DUMP_AJAX:
                    print 'AJAX INVALID RESPONSE TYPE'
                    print 'original response:', results.__class__.__name__
                    print results
                    print 'AJAX result:', response
                return AjaxErrorResponse(response)

            if settings.SCULPT_DUMP_AJAX:
                print 'AJAX result:', results.content
            return results
            
        except Exception, e:
            # decide whether to include backtraces for AJAX exceptions;
            # we use the regular Django settings.DEBUG because the same
            # switch controls debug backtrace display for page requests
            # too, and is always OFF in production
            if settings.DEBUG:
                # sys.exc_info() returns a tuple (type, exception object, stack trace)
                # traceback.format_exception() formats the result in plain text, as a list of strings
                import sys
                import traceback
                backtrace_text = ''.join(traceback.format_exception(*sys.exc_info()))
                if settings.SCULPT_DUMP_AJAX:
                    print backtrace_text
                return AjaxExceptionResponse({ 'code': 0, 'title': e.__class__.__name__, 'message': str(e), 'backtrace': backtrace_text })
                
            else:
                # NOT in debug mode, reveal NOTHING
                #
                # we have a problem, though; we really, really need
                # for this backtrace to be mailed to the admins, so
                # we have two choices: either re-raise the exception
                # and let Django's code email the backtrace, relying
                # on the client-side code to see it's a 500 and show
                # an error message, OR burrow into the default WSGI
                # handler's exception logging mechanism to get the
                # email out while still replying with a sane error
                # message.
                #
                # we're masochists: we'll take door number 2

                # this is how Django logs the exception; see code in
                # django.core.handlers.base
                import logging
                import sys
                
                logger = logging.getLogger('django.request')
                logger.error('Internal Server Error: %s', request.path,
                    exc_info=sys.exc_info(),
                    extra={
                        'status_code': 500,
                        'request': request
                    }
                )

                # give back a nice formatted response, AJAX-style
                response = { 'code': 0, 'title': 'Exception', 'message': 'An exception occurred.' }
                if settings.SCULPT_DUMP_AJAX:
                    print repr(response)
                return AjaxExceptionResponse(response)

# an AJAX response-generating view
#
# This is a generic view that expects derived classes to
# populate a context, and then get configuration data from
# urls.py that tells what (modal, toast, HTML updates) to
# render and send back to the client. It's good for quick
# prototyping but also for production code.
#
class AjaxResponseView(AjaxView):
    modal = None
    toast = None
    updates = None

    # shared setup based on request parameters;
    #
    # If you need to validate IDs in the URL and fetch
    # records for both GET and POST, this is the place
    # to do that. This is NOT the same as the __init__
    # method. Django creates a new View object with
    # each request, and the __init__ method receives
    # all the parameters from the urls.py .as_view()
    # call. This method received the additional
    # parameters from URL keyword-matching and from
    # the extra parameters dict in the urls.py url()
    # invocation. (The latter should be considered
    # deprecated now that parameters can be passed to
    # the View constructor, as the view function from
    # the .as_view() invocation validates parameters,
    # and the extra-parameters dict does not.)
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user
    #
    def prepare_request(self, *args, **kwargs):
        pass

    # prep the context
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user
    # NOTE: this serves a similar purpose to Django's
    # TemplateView.get_context_data(), but this does
    # not derive from TemplateView so it's not available.
    #
    def prepare_context(self, context):
        pass

    # shortcut to render to string using the defined templates
    # for modal, toast, and updates, and return the correct
    # AJAX response
    def prepare_response(self, context = None):
        if context == None:
            context = {}
        if not isinstance(context, Context):
            # must have a Context instance to render templates
            context = RequestContext(self.request, context)

        # prepare all-in-one configuration
        response_data = {}
        if self.modal:
            response_data['modal'] = self.modal
        if self.toast:
            response_data['toast'] = self.toast
        if self.updates:
            response_data['updates'] = self.updates
            
        return AjaxMixedResponse.create(context, response_data)

    # handle POST request (the "normal" request)
    def post(self, request, *args, **kwargs):

        # do request setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, JsonResponse):
            return rv

        # set up context
        context = {}
        initial = {}
        rv = self.prepare_context(context)
        if isinstance(rv, JsonResponse):
            return rv

        # render to AJAX response; if this returns anything
        # other than a JsonResponse, the base class code
        # will complain
        return self.prepare_response(context)

# an AJAX form view class
#
# AJAX forms return a rendered HTML page on GET but process form
# submission data on POST and return a JSON result; the sculpt-ajax
# handler on the client will then process the errors and highlight
# the appropriate fields in the form. Successful form submission
# will direct the player to the next step.
#
# when deriving from this view, you must provide:
#   template_name   an HTML template path (for GET)
#   form_class      a form class (a reference to the class,
#                   not just the name as a string)
#   target_url      where to go after the POST succeeds; if None,
#                   a response is generated like AjaxResponseView
#
class AjaxFormView(AjaxResponseView):
    
    # these attributes must be present (but unfilled) or the
    # as_view method will not allow them to be set
    template_name = None
    form_class = None
    target_url = None

    # crispy forms allows a lot of control over form
    # rendering via its FormHelper, but sometimes in a
    # particular view you need to override these; this
    # dict will be applied as attributes to the FormHelper
    # after it's been created, so you don't have to create
    # one-off derived form classes
    helper_attrs = {}

    # similarly, it may be necessary to pass in additional
    # parameters on the form object itself (e.g. prefix)
    # so we make these available here
    # NOTE: these are passed during creation, not applied
    # afterwards
    form_attrs = {}
    
    # sometimes we want a form view to only render form(s),
    # not process them (especially if we are including more
    # than one form on the page); set this flag to True to
    # block the normal POST handling
    #
    # NOTE: this pretty much turns this into a non-AJAX
    # request, since only the GET works and returns raw
    # HTML, but it allows the same form base classes to be
    # used.
    #
    render_only = False
    
    #
    # override these to provide custom handling for your form
    #

    # shared setup based on request parameters
    # (inherited from AjaxResponseView)
    #
    #def prepare_request(self, *args, **kwargs):
    #    pass

    # prep the context and initial form data
    #
    # NOTE: you don't have to put form into context, the
    # boilerplate will do that
    #
    # NOTE: this IS NOT called for POST because POST
    # will not render HTML, UNLESS you are falling back
    # on AjaxResponseView-style responses, in which case
    # it will be called AFTER form validation, BEFORE
    # any modal/toast/updates rendering
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user
    #
    # NOTE: this is NOT inherited from AjaxResponseView
    # as its call signature differs (includes initial)
    #
    def prepare_context(self, context, initial):
        pass

    # after the form object has been created, it may
    # need to be modified before being rendered or
    # validated; do that here
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user
    #
    def prepare_form(self, form):
        pass

    # when a form has been successfully validated, do
    # something with the data; this is the most important
    # function to override and will typically save the
    # data or at least update target_url
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user;
    # you may also return a string to indicate a
    # different target URL than the default
    #
    def process_form(self, form):
        pass
    
    # when a form is being partially validated you may
    # want to do something (and usually this is very
    # different from what you do with a fully-valid form)
    #
    def process_partial_form(self, form):
        pass
    
    #
    # boilerplate, so you don't have to keep writing it
    #
    
    # basic GET handler: set up the form and
    # context and render the view
    def get(self, request, *args, **kwargs):

        # do GET/POST combined setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, (HttpResponse)):
            return rv
        
        # set up context and initial form data
        context = {}
        initial = {}
        rv = self.prepare_context(context, initial)
        if isinstance(rv, (HttpResponse)):
            return rv

        # create form(s) and give the derived class a chance
        # to modify it
        form = self.form_class(initial = initial, **self.form_attrs)
        context['form'] = form

        # Allows you to prepopulate the helper attributes before you prepare the form
        for k in self.helper_attrs:
            setattr(form.helper, k, self.helper_attrs[k])

        rv = self.prepare_form(form)
        if isinstance(rv, (HttpResponse)):
            return rv
        
        # render the template and give back a response
        return render(request, self.template_name, context)
        
    # basic POST handler: validate the form
    # and dispatch to a success handler
    def post(self, request, *args, **kwargs):
    
        # if POST has been blocked due to this being a view-
        # only form, pretend this function doesn't exist
        if self.render_only:
            return self.http_method_not_allowed(request, *args, **kwargs)
    
        # if this is a partial validation request, record that
        # NOTE: at this point, the last field's name has
        # not been validated
        if '_partial' in request.GET:
            self._partial_validation_last_field = request.GET['_partial']
        
        # do GET/POST combined setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, JsonResponse):
            return rv
        
        # create the form based on the submitted data
        # (automatically pass in files if they were submitted)
        if hasattr(request, 'FILES') and request.FILES:
            form = self.form_class(request.POST, request.FILES, **self.form_attrs)
        else:
            form = self.form_class(request.POST, **self.form_attrs)
        rv = self.prepare_form(form)
        if isinstance(rv, JsonResponse):
            return rv
        
        if self.is_partial_validation:
            # we're only doing partial validation
            is_partially_valid = form.is_partially_valid(self._partial_validation_last_field)
            
            # call any processing needed for this partial form
            rv = self.process_partial_form(form)
            if isinstance(rv, JsonResponse):
                return rv
            
            # whether we are valid or not, we actually go ahead 
            # and return the form error response, so that existing
            # successfully-validated fields can be highlighted
            return AjaxFormErrorResponse(form, last_field = self._partial_validation_last_field, focus_field = request.GET.get('_focus'))
                
        else:        
            # validate the form and return an error response
            # NOTE: THIS MEANS ALL VALIDATION MUST BE DONE
            # IN THE FORM CLASS
            if not form.is_valid():
                return AjaxFormErrorResponse(form)
            
        # a valid form will usually require something to
        # be done with its data
        rv = self.process_form(form)
        if rv is None:
            # this means use the default target_url
            rv = self.target_url

        if rv is None:
            # no JsonResponse, no target_url string...
            # fall back to AjaxResponseView-style
            context = {}
            initial = {}
            rv = self.prepare_context(context, initial)
            if isinstance(rv, (HttpResponse)):
                # in case the context-creating needs to bail
                return rv
            rv = self.prepare_response(context)

        if isinstance(rv, JsonResponse):
            # we now have a valid JSON response; stop
            return rv

        if isinstance(rv, basestring):
            # we could just overwrite self.target_url
            # but it's trivial to return the redirect
            # in one step...
            return AjaxRedirectResponse(rv)

        # default handling is to go to the target URL
        return AjaxRedirectResponse(self.target_url)

    # test whether this request is trying to do partial
    # validation; use this in your overridden functions to
    # avoid accidentally terminating partial validation
    # by returning AjaxMixedResponse objects
    @property
    def is_partial_validation(self):
        return self._partial_validation_last_field != None

    # the internal tracking field that remembers the
    # last field for validation; if you MUST check this,
    # you can, but you should use is_partial_validation
    # instead
    _partial_validation_last_field = None
    

# an AJAX form view class that handles multiple forms at once
#
# This is similar to AjaxFormView except that it explicitly
# expects multiple forms to be included on the page. Generally
# these will be submitted to separate URLs, but this is not a
# requirement and this class provides some semi-automatic
# routing of form processing. To enable this, you must
# include in EACH form a hidden form_alias field, the value
# of which will be supplied by the boilerplate.
#
# When deriving from this view, you must provide:
#   template_name   an HTML template path
#   form_classes    a dict; keys are form aliases (relevant
#                   only to the view and its template) and
#                   values are tuples with these elements:
#     form_class    a form class (a reference to the class,
#                   not just the name as a string)
#     helper_attrs  a dict of attrs applied to the Crispy
#                   form helper object as attributes (not
#                   to be confused with the Crispy attrs
#                   attribute)
#                   (of special note is form_action, the
#                   URL to which the form will be POSTed)
#     target_url    where to go after a POST of this form
#                   succeeds; if None, uses view default
#     form_attrs    a dict of additional parameters to
#                   pass to the form object during creation
#                   (optional)
#
# This class does not derive from AjaxFormView but rather
# directly from AjaxView. There is significant code overlap,
# though. The prepare_context, prepare_form, and process_form
# methods can be customized per form by appending _<alias>
# to the respective function. On POST, the default handler
# will look for a POSTed element of form_alias which MUST be
# included; if it matches one of the form aliases in the view,
# process_form will be routed to that custom function if it
# exists.
#
# NOTE: since form aliases are used to construct Python
# method names, you should use standard Python style for them.
#
# NOTE: on GET requests, ALL forms are processed; on POST
# requests, only ONE form can be processed (because only one
# is submitted by the browser).
#
# NOTE: if you care about the order in which forms are
# processed, pass in a SortedDict for form_classes instead
# of a dict.
#
class AjaxMultiFormView(AjaxView):
    
    # these attributes must be present (but unfilled) or the
    # as_view method will not allow them to be set
    template_name = None
    form_classes = None
    target_url = None
    
    # sometimes we want a form view to only render form(s),
    # not process them (especially if we are including more
    # than one form on the page); set this flag to True to
    # block the normal POST handling
    #
    # NOTE: this pretty much turns this into a non-AJAX
    # request, since only the GET works and returns raw
    # HTML, but it allows the same form base classes to be
    # used.
    #
    render_only = False
    
    #
    # override these to provide custom handling for your form
    #

    # shared setup based on request parameters
    # (similar to AjaxResponseView, but we don't inherit
    # from that)
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user
    #
    def prepare_request(self, *args, **kwargs):
        pass

    # prep the context and initial form data
    #
    # NOTE: you probably don't want to override this,
    # but provide prepare_context_<alias> instead
    #
    # NOTE: this is called once per form alias; context
    # will be the same dict (updatable by each method)
    # but initial will be unique per form alias
    #
    # NOTE: you don't have to put forms into context, the
    # boilerplate will do that
    #
    # NOTE: this IS NOT called for POST because POST
    # will not render HTML
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user,
    # aborting all other form processing
    #
    def prepare_context(self, context, initial, form_alias):
        if form_alias in self.form_classes:
            method_name = 'prepare_context_%s' % form_alias
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(context, initial)
            else:
                method_name = 'prepare_context__default'
                if hasattr(self, method_name) and callable(getattr(self, method_name)):
                    return getattr(self, method_name)(context, initial, form_alias)

    # and sometimes we need to set some global context
    # stuff, aside from all the forms, especially when
    # the list of forms is dynamically generated
    # NOTE: there's no initial data and no form context
    def prepare_context__all(self, context):
        pass

    # after the form object has been created, it may
    # need to be modified before being rendered or
    # validated; do that here
    #
    # NOTE: you probably don't want to override this,
    # but provide prepare_form_<alias> instead
    #
    # NOTE: this is called once per form alias
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type (for POST) or
    # HttpResponse type (for GET), processing will stop
    # and that response sent back to the user, aborting
    # all other form processing
    #
    def prepare_form(self, form, form_alias):
        if form_alias in self.form_classes:
            method_name = 'prepare_form_%s' % form_alias
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form)
            else:
                method_name = 'prepare_form__default'
                if hasattr(self, method_name) and callable(getattr(self, method_name)):
                    return getattr(self, method_name)(form, form_alias)

    # when a form has been successfully validated, do
    # something with the data; this is the most important
    # function to override and will typically save the
    # data or at least update target_url
    #
    # NOTE: you probably don't want to override this,
    # but provide process_form_<alias> instead
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user;
    # you may also return a string to indicate a
    # different target URL than the default
    #
    def process_form(self, form, form_alias):
        if form_alias in self.form_classes:
            method_name = 'process_form_%s' % form_alias
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form)
            else:
                method_name = 'process_form__default'
                if hasattr(self, method_name) and callable(getattr(self, method_name)):
                    return getattr(self, method_name)(form, form_alias)
    
    # similarly, if you want to process partial form
    # data, provide a process_partial_form_<alias>
    # method; if it returns an AjaxResponse object,
    # that will be given to the browser
    #
    # the notes on process_form apply to this as well
    #
    def process_partial_form(self, form, form_alias):
        if form_alias in self.form_classes:
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form)
            else:
                method_name = 'process_partial_form__default'
                if hasattr(self, method_name) and callable(getattr(self, method_name)):
                    return getattr(self, method_name)(form, form_alias)
    
    #
    # boilerplate, so you don't have to keep writing it
    #
    
    # pull out the form configuration data from a form_alias
    # definition (accepts either tuple or dict)
    def extract_form_data(self, form_data):
        if isinstance(form_data, dict):
            form_class = form_data['form_class']    # required
            helper_attrs = form_data.get('helper_attrs')
            target_url = form_data.get('target_url')
            form_attrs = form_data.get('form_attrs', {})
            return (form_class, helper_attrs, target_url, form_attrs)
        else:
            return form_data

    # basic GET handler: set up the form and
    # context and render the view
    def get(self, request, *args, **kwargs):

        # do GET/POST combined setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, HttpResponse):
            return rv
        
        # set up context and initial form data
        context = {}
        initials = {}
        for form_alias,form_data in self.form_classes.iteritems():
            self.form_data = form_data              # in case handler needs it
            form_class, helper_attrs, target_url, form_attrs = self.extract_form_data(form_data)
            
            # extra check: sometimes we forget to include
            # AjaxFormAliasMixin for forms we want to use
            # with this view; it's not always an error if
            # the form action is directed elsewhere, but
            # it can be helpful to flag these
            if form_class is None:
                raise Exception('form_class cannot be None for form_alias %s' % form_alias)
            if not issubclass(form_class, AjaxFormAliasMixin) and settings.DEBUG:
                print 'WARNING: %(form_class_name)s is not a sub-class of AjaxFormAliasMixin' % { 'form_class_name': form_class.__name__ }

            initials[form_alias] = { 'form_alias': form_alias }
            rv = self.prepare_context(context, initials[form_alias], form_alias)
            if isinstance(rv, HttpResponse):
                return rv

        # and the global context prep, after all the
        # forms are done
        rv = self.prepare_context__all(context)
        if isinstance(rv, HttpResponse):
            return rv

        # create form(s) and give the derived class a chance
        # to modify it
        #
        # NOTE: we use an OrderedDict here in case the derived
        # view class used an OrderedDict to control the order
        # forms are inserted. Django makes it impossible to
        # do index lookups by variable within a template, so
        # we need to be able to pass in a list of actual form
        # objects; the easiest way is to order the set of forms
        # we're actually using, if the derived view needs it.
        # If the source form_classes is not an OrderedDict but
        # a regular dict, no harm is done.
        #
        context['forms'] = OrderedDict()
        for form_alias,form_data in self.form_classes.iteritems():
            self.form_data = form_data              # in case handler needs it
            form_class, helper_attrs, target_url, form_attrs = self.extract_form_data(form_data)
            if helper_attrs == None:
                helper_attrs = {}
            if 'prefix' not in form_attrs:
                form_attrs['prefix'] = form_alias
            form = form_class(initial = initials[form_alias], **form_attrs)
            context['forms'][form_alias] = form

            # extra step: apply Crispy helper attributes
            for k in helper_attrs:
                setattr(form.helper, k, helper_attrs[k])

            rv = self.prepare_form(form, form_alias)
            if isinstance(rv, HttpResponse):
                return rv
        
        # render the template and give back a response
        return render(request, self.template_name, context)
        
    # basic POST handler: validate the form
    # and dispatch to a success handler
    def post(self, request, *args, **kwargs):
    
        # if POST has been blocked due to this being a view-
        # only form, pretend this function doesn't exist
        if self.render_only:
            return self.http_method_not_allowed(request, *args, **kwargs)
    
        # if this is a partial validation request, record that
        # NOTE: at this point, the last field's name has
        # not been validated
        if '_partial' in request.GET:
            self._partial_validation_last_field = request.GET['_partial']
        
        # do GET/POST combined setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, JsonResponse):
            return rv
        
        # figure out which form is submitted
        # NOTE: we require the form_alias field to be
        # present
        # NOTE: if we're using prefix (which, by default,
        # we always are) then there won't BE a form_alias;
        # instead there will be <alias>-form_alias and we
        # need to search for it
        form_alias = None
        for alias in self.form_classes.iterkeys():
            alias_field = alias + '-form_alias'
            if alias_field in request.POST and request.POST[alias_field] == alias:
                form_alias = alias
                break
                
        # fallback position: unprefixed field
        if form_alias == None:
            if 'form_alias' not in request.POST or request.POST['form_alias'] not in self.form_classes:
                # we're going to reject this request because
                # we don't know which form it belongs to, but
                # it's possible this is due to a programming
                # mistake like not including AjaxFormAliasMixin
                # in the form's inheritance path, so we want
                # to be more explicit in calling this out
                if settings.DEBUG:
                    print 'AJAX FORM ERROR: no form_alias could be found; did you forget to derive from AjaxFormAliasMixin?'
                return self.http_method_not_allowed(request, *args, **kwargs)

            # else we know this value is good; use the
            # unprefixed form_alias
            form_alias = request.POST['form_alias']

        form_data = self.form_classes[form_alias]
        form_class, helper_attrs, target_url, form_attrs = self.extract_form_data(form_data)
        self.form_data = form_data              # in case handler needs it
        if target_url == None:
            # this form doesn't have a specific target URL;
            # use the class-wide one
            target_url = self.target_url
        if 'prefix' not in form_attrs:
            form_attrs['prefix'] = form_alias

        # create the form based on the submitted data
        form = form_class(request.POST, **form_attrs)
        rv = self.prepare_form(form, form_alias)
        if isinstance(rv, JsonResponse):
            return rv
        
        if self.is_partial_validation:
            # we're only doing partial validation
            is_partially_valid = form.is_partially_valid(self._partial_validation_last_field)
            
            # call any processing needed for this partial form
            rv = self.process_partial_form(form, form_alias)
            if isinstance(rv, JsonResponse):
                return rv
            
            # whether we are valid or not, we actually go ahead 
            # and return the form error response, so that existing
            # successfully-validated fields can be highlighted
            return AjaxFormErrorResponse(form, last_field = self._partial_validation_last_field, focus_field = request.GET.get('_focus'))
                
        else:        
            # validate the form and return an error response
            # NOTE: THIS MEANS ALL VALIDATION MUST BE DONE
            # IN THE FORM CLASS
            if not form.is_valid():
                return AjaxFormErrorResponse(form)
            
        # a valid form will usually require something to
        # be done with its data
        rv = self.process_form(form, form_alias)
        
        #**** MAKE LIKE AjaxFormView AND FALL BACK TO AjaxResponseView
        if isinstance(rv, JsonResponse):
            return rv
        if isinstance(rv, basestring):
            # we could just overwrite self.target_url
            # but it's trivial to return the redirect
            # in one step...
            return AjaxRedirectResponse(rv)

        # default handling is to go to the target URL
        return AjaxRedirectResponse(target_url)

    # test whether this request is trying to do partial
    # validation; use this in your overridden functions to
    # avoid accidentally terminating partial validation
    # by returning AjaxResponse objects
    @property
    def is_partial_validation(self):
        return self._partial_validation_last_field != None

    # the internal tracking field that remembers the
    # last field for validation; if you MUST check this,
    # you can, but you should use is_partial_validation
    # instead
    _partial_validation_last_field = None
    
