from django.db import transaction, DatabaseError
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import RequestContext, Context
from django.template.loader import get_template, render_to_string
from django.views.generic import View

from sculpt.ajax import settings
from sculpt.ajax.forms import AjaxFormAliasMixin
from sculpt.ajax.responses import AjaxSuccessResponse, AjaxHTMLResponse, AjaxModalResponse, AjaxRedirectResponse, AjaxMixedResponse, AjaxErrorResponse, AjaxExceptionResponse, AjaxFormErrorResponse
from sculpt.common import Enumeration

from collections import OrderedDict
import copy

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

    # There are three use cases for any particular method:
    #   1. it is never an AJAX request
    #   2. it is sometimes an AJAX request
    #   3. it is always an AJAX request
    #
    # For most of our AJAX views, it's the third case. This is
    # the simplest and most predictable, and for non-form requests
    # we pretty much just allow POST and it's always AJAX. For
    # forms, we might say GET is never AJAX and POST is always
    # AJAX; this again is straightforward.
    #
    # We want to catch programming mistakes that return JSON
    # reponses to non-AJAX requests and non-JSON responses to
    # AJAX requests, which means we need to know which category
    # each method belongs to. If we use SNIFF_AJAX, then we
    # will look at the request to see if it claims to be AJAX
    # or not.
    #
    AJAX_RESTRICTIONS = Enumeration(
            (0, 'NEVER_AJAX'),
            (1, 'SNIFF_AJAX'),
            (2, 'ALWAYS_AJAX'),
        )

    # list all request methods that we want to mark as AJAX; if
    # we don't list them here, the default is NEVER_AJAX and we
    # will not only not check for a JSON response, we won't
    # wrap exceptions in a JSON wrapper, either
    #
    # NOTE: you can reset the AJAX restrictions mid-request, if
    # you discover a request that is usually AJAX turns out not
    # to be (e.g. file upload)
    #
    ajax_restrictions = {
            'POST': AJAX_RESTRICTIONS.ALWAYS_AJAX,
        }

    # a wrapper to answer the question as to whether something is
    # an AJAX request or not, taking into account the request
    # method and the request.is_ajax() results; thus if a method
    # is marked above as ALWAYS_AJAX, this method will return
    # True regardless of what's in the request
    @property
    def is_ajax(self):
        restrictions = self.ajax_restrictions.get(self.request.method, self.AJAX_RESTRICTIONS.NEVER_AJAX)
        if restrictions == self.AJAX_RESTRICTIONS.NEVER_AJAX:
            return False
        elif restrictions == self.AJAX_RESTRICTIONS.SNIFF_AJAX:
            return self.request.is_ajax()
        else:
            return True

    # similary we often want to be able to ask what the base class
    # of a response should be; this is based on whether it's AJAX
    # or not
    @property
    def response_base_class(self):
        if self.is_ajax:
            return JsonResponse
        else:
            return HttpResponse

    # special handling: if an exception occurs in an AJAX request, we
    # DO NOT want to return an exception as Django's default HTML-
    # formatted response. Instead, catch the exception and return
    # an AJAX-formatted error. However, we can't do this in a post()
    # handler because the derived class gets first crack at handling
    # it, and that's the code we need to wrap in try/except. So we
    # do the wrapping here, in dispatch.
    def dispatch(self, request, *args, **kwargs):

        # if we know this call is not AJAX, we don't need to do
        # any wrapping of the output except possibly to catch
        # DatabaseError exceptions
        if not self.is_ajax:
            try:
                return super(AjaxView, self).dispatch(request, *args, **kwargs)
            except DatabaseError, e:
                if settings.SCULPT_AJAX_REPORT_HTML_DATABASE_ERRORS:
                    # give back a nice formatted response, HTML-style
                    from sculpt.ajax.messaging import render_message
                    response = render_message(request, 'error', 'database-contention', is_ajax = False, response_code = 500)
                    return response

                else:
                    # we're not supposed to catch these, re-raise the
                    # error in the original context
                    raise
            
        # otherwise it's a post (or at least something we're
        # supposed to wrap); trap exceptions
        try:
            # spew some debug data, perhaps
            if settings.SCULPT_AJAX_DUMP_REQUESTS:
                raw_uri = request.META['RAW_URI'] if 'RAW_URI' in request.META else request.META['PATH_INFO']
                if request.META.get('CONTENT_TYPE','').startswith('multipart/form-data'):
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

            if not isinstance(results, self.response_base_class):
                # we want to make sure all AjaxView handlers return
                # a response in the correct form; if not, we want
                # to trap those errors early in development rather
                # than let them skate by
                #
                # NOTE: we return this rather than raise it, because
                # we don't have a backtrace (it's not helpful) and
                # because it's already formatted as an error response
                #
                # NOTE: we deliberately look at self.response_base_class
                # even though we're in the "is_ajax" branch, because
                # the view class may have reset the AJAX restrictions
                # on this request
                #
                response = { 'code': 1, 'title': 'Invalid Response Type', 'message': 'Request generated an invalid response type (%s)' % results.__class__.__name__ }
                if settings.SCULPT_AJAX_DUMP_REQUESTS:
                    print 'AJAX INVALID RESPONSE TYPE'
                    print 'original response:', results.__class__.__name__
                    print results
                    print 'AJAX result:', response
                return AjaxErrorResponse(response)

            if settings.SCULPT_AJAX_DUMP_REQUESTS:
                print 'AJAX result:', results.content
            return results
            
        except Exception, e:
            # decide whether to include backtraces for AJAX exceptions;
            # we use the regular Django settings.DEBUG because the same
            # switch controls debug backtrace display for page requests
            # too, and is always OFF in production
            #
            # NOTE: this debug setting takes precedence over whether the
            # exception is a database error (DatabaseError) so that
            # the backtrace can be presented. This is important because
            # DatabaseError can also be thrown when a unique constraint
            # is violated, not just when a transaction can't be completed
            # in a timely fashion.
            #
            if settings.DEBUG:
                # sys.exc_info() returns a tuple (type, exception object, stack trace)
                # traceback.format_exception() formats the result in plain text, as a list of strings
                import sys
                import traceback
                backtrace_text = ''.join(traceback.format_exception(*sys.exc_info()))
                if settings.SCULPT_AJAX_DUMP_REQUESTS:
                    print backtrace_text
                return AjaxExceptionResponse({ 'code': 0, 'title': e.__class__.__name__, 'message': str(e), 'backtrace': backtrace_text })
                
            elif isinstance(e, DatabaseError) and settings.SCULPT_AJAX_REPORT_AJAX_DATABASE_ERRORS:
                # NOT in debug mode, but this is an DatabaseError;
                # we don't directly log these and and we at least
                # report to the user something more generic
                if settings.SCULPT_AJAX_DUMP_REQUESTS:
                    print 'AJAX DatabaseError:', str(e)
                
                # give back a nice formatted response, AJAX-style
                from sculpt.ajax.messaging import render_message
                response = render_message(request, 'error', 'database-contention', is_ajax = True, response_code = 500)
                return response

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
                if settings.SCULPT_AJAX_DUMP_REQUESTS:
                    print repr(response)
                return AjaxExceptionResponse(response)


# sometimes we need GET or POST requests to be complete
# atomic transactions; for cases where we aren't otherwise
# changing the GET or POST operations, make it easy to
# do this
#
class AtomicGetMixin(object):

    @transaction.atomic
    def get(self, *args, **kwargs):
        return super(AtomicGetMixin, self).get(*args, **kwargs)


class AtomicPostMixin(object):

    @transaction.atomic
    def post(self, *args, **kwargs):
        return super(AtomicPostMixin, self).post(*args, **kwargs)


# an AJAX response-generating view
#
# This is a generic view that expects derived classes to
# populate a context, and then get configuration data from
# urls.py that tells what (modal, toast, HTML updates) to
# render and send back to the client. It's good for quick
# prototyping but also for lightweight production code.
#
class AjaxResponseView(AjaxView):
    modal = None
    toast = None
    updates = None
    context = None
    updates_attrs = None

    # shared setup based on request parameters;
    #
    # If you need to validate IDs in the URL and fetch
    # records for both GET and POST, this is the place
    # to do that. This is NOT the same as the __init__
    # method. Django creates a new View object with
    # each request, and the __init__ method receives
    # all the parameters from the urls.py .as_view()
    # call. This method receives the additional
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
    # NOTE: this is only if you need to programmatically
    # add to the context; if you simply need to put a few
    # static things into the context, you can set that
    # when you call as_view() instead.
    #
    def prepare_context(self, context):
        pass

    # shortcut to render to string using the defined templates
    # for modal, toast, and updates, and return the correct
    # AJAX response
    def prepare_response(self, context = None, results = None, updates_attrs = None, default_html = None):
        if context is None:
            context = {}
        if not isinstance(context, Context):
            # must have a Context instance to render templates
            context = RequestContext(self.request, context)

        if updates_attrs is None:
            updates_attrs = self.updates_attrs

        # prepare all-in-one configuration
        response_data = {}
        if self.modal:
            response_data['modal'] = self.modal
        if self.toast:
            response_data['toast'] = self.toast
        if self.updates:
            response_data['updates'] = self.updates
        if results:
            response_data['results'] = results
            
        return AjaxMixedResponse.create(context, response_data, updates_attrs = updates_attrs, default_html = default_html)

    # handle POST request (the "normal" request)
    def post(self, request, *args, **kwargs):

        # do request setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, self.response_base_class):
            return rv

        # set up context
        #
        # NOTE: if a default context has been provided, it
        # must be deep-copied prior to use in case the
        # prepare_context() method needs to modify it. This
        # is inefficient if it's not going to be modified.
        #
        if self.context is None:
            context = {}
        else:
            context = copy.deepcopy(self.context)
        
        rv = self.prepare_context(context)
        if isinstance(rv, self.response_base_class):
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
# will direct the user to the next step.
#
# When deriving from this view, you must provide:
#   template_name   an HTML template path (for GET)
#   form_class      a form class (a reference to the class,
#                   not just the name as a string)
#   target_url      where to go after the POST succeeds; if None,
#                   a response is generated like AjaxResponseView
#
# Optionally, you may also include:
#   form_attrs      additional parameters for form creation
#   helper_attrs    additional parameters for form helper creation
#
# Alternatively you may provide a dict (or OrderedDict) of form
# aliases and form creation data (the same template_name, form_class,
# target_url, form_attrs, and helper_attrs as for a single form)
# and all of the forms will be created, with the form_alias used as
# a prefix for each form. If you use an OrderedDict instead of just
# a dict you can iterate over it in the same order that you added
# to it.
#
# Multiple forms are intended for situations where the user only
# intends to submit a single form on the page rather than all of
# them at once. There are other more complex use cases that involve
# processing partially-valid forms. A tutorial/cookbook should
# be written.
#
class AjaxFormView(AjaxResponseView):
    
    # when only a single form is present, these variables
    # can be set as a convenience rather than defining
    # form_classes with just one entry
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

    # similarly, sometimes we want a form view to only
    # process form(s), not render them (especially if the
    # form is rendered in another view); set this flag to
    # True to block the normal GET handling
    #
    process_only = False

    # sometimes we want to do all of our processing as though
    # it's partial validation, but occasionally the browser
    # may do a full submission if the user presses RETURN;
    # enable this setting to force all submissions to be
    # treated as partial submissions
    #
    always_partially_validate = False
    
    # instead of a single form we might have multiple forms;
    # this should be a dict or OrderedDict with form aliases
    # as keys
    #
    # NOTE: if this is None, template_name, form_class,
    # target_url, helper_attrs, and form_attrs should NOT
    # be used.
    #
    form_classes = None

    # and a very common pattern is to create templates for
    # forms, and re-use the template for multiple copies of
    # the same form (for multi-record editing); for these,
    # it's a good idea to set form_type in each template to
    # a meaningful thing, and form_type will be used in place
    # of form_alias when invoking the various overridable
    # methods for each form
    #
    form_class_templates = None
    
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
    # This is called once for each form, with the form_alias
    # parameter indicating which form it's being invoked
    # for. In a single-form view, form_alias will be None.
    # It's reasonable to override this for a single-form
    # view, but for a multi-form view, it may be more
    # convenient to instead provide a prepare_context_<alias>
    # method with the same signature, and allow the code
    # here to dispatch it. You can also override the
    # prepare_default_context method to write your own
    # default case without replacing the entire dispatching
    # mechanism. In cases where multiple copuie
    #
    # At the time this function is called, the form has
    # not been created.
    #
    # This method is normally not called for POST because
    # POST normally doesn't render HTML. However, if you are
    # falling back to the AjaxResponseView-style response,
    # it WILL be called just prior to that response being
    # rendered.
    #
    # NOTE: a normal return value should be None, but
    # if you return an HttpResponse type, processing
    # will stop and that response sent back to the user
    #
    # NOTE: this is NOT inherited from AjaxResponseView
    # as its call signature differs
    #
    def prepare_context(self, context, initial, form_alias):
        if form_alias is not None and form_alias in self.form_classes:
            method_name = 'prepare_context_%s' % self.form_classes[form_alias].get('form_type', form_alias)
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(context, initial, form_alias)
            else:
                return self.prepare_default_context(context, initial, form_alias)

    # default handler if no form-specific one is defined
    def prepare_default_context(self, context, initial, form_alias):
        pass

    # prep the context, separate from all forms
    #
    # In a multi-form view it's often necessary to add
    # things to the context which aren't tied to any
    # specific form; override this method to do so.
    # For single-form views, it's simpler just to add
    # to the context directly in prepare_context().
    #
    # NOTE: a normal return value should be None, but
    # if you return an HttpResponse type, processing
    # will stop and that response sent back to the user
    #
    def prepare_nonform_context(self, context):
        pass

    # after the form object has been created, it may
    # need to be modified before being rendered or
    # validated; do that here
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user
    #
    def prepare_form(self, form, form_alias):
        if form_alias is not None and form_alias in self.form_classes:
            method_name = 'prepare_form_%s' % self.form_classes[form_alias].get('form_type', form_alias)
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form, form_alias)
            else:
                return self.prepare_default_form(form, form_alias)

    # default handler if no form-specific one is defined
    def prepare_default_form(self, form, form_alias):
        pass

    # When a form has been successfully validated, do
    # something with the data; this is the most important
    # function to override and will typically save the
    # data or at least update target_url.
    #
    # In a POST request this is only called once, for the
    # single form that was actually submitted.
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user;
    # you may also return a string to indicate a
    # different target URL than the default
    #
    def process_form(self, form, form_alias):
        if form_alias is not None and form_alias in self.form_classes:
            method_name = 'process_form_%s' % self.form_classes[form_alias].get('form_type', form_alias)
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form, form_alias)
            else:
                return self.process_default_form(form, form_alias)

    # default handler if no form-specific one is defined
    def process_default_form(self, form, form_alias):
        pass
    
    # when a form is determined to be invalid, it might
    # still be desirable to do some processing before
    # returning an error response
    #
    # NOTE: a normal return value should be None, but
    # if you return a JsonResponse type, processing
    # will stop and that response sent back to the user;
    # you may also return a dict that will be passed as
    # extra parameters to the AjaxFormErrorResponse
    # constructor in case you want to provide toast,
    # HTML updates, or field value updates
    #
    def process_invalid_form(self, form, form_alias):
        if form_alias in self.form_classes:
            method_name = 'process_invalid_form_%s' % self.form_classes[form_alias].get('form_type', form_alias)
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form)
            else:
                return self.process_default_invalid_form(form, form_alias)

    # default handler if no form-specific one is defined
    def process_default_invalid_form(self, form, form_alias):
        pass

    # when a form is being partially validated you may
    # want to do something (and usually this is very
    # different from what you do with a fully-valid form)
    #
    def process_partial_form(self, form, form_alias):
        if form_alias is not None and form_alias in self.form_classes:
            method_name = 'process_partial_form_%s' % self.form_classes[form_alias].get('form_type', form_alias)
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                return getattr(self, method_name)(form, form_alias)
            else:
                return self.process_default_partial_form(form, form_alias)

    # default handler if no form-specific one is defined
    def process_default_partial_form(self, form, form_alias):
        pass
    
    # this is a wrapper around the Django render function,
    # in case GET requests need to return AJAX responses
    def render(self, context):
        if self.template_name is None and (self.updates is not None or self.modal is not None or self.toast is not None):
            # this is intended to be an AJAX resopnse
            return self.prepare_response(context)

        else:
            # this is a standard HTML response
            return render(self.request, self.template_name, context)

    #
    # boilerplate, so you don't have to keep writing it
    #
    
    # constructor is invoked when request is dispatched
    # to view wrapper function
    def __init__(self, *args, **kwargs):

        # base class copies kwargs to attributes
        super(AjaxFormView, self).__init__(*args, **kwargs)

        # if we've been given both a single form class and
        # a collection, complain
        if self.form_class is not None and self.form_classes is not None:
            raise ImproperlyConfigured('Cannot specify both a single form class and multiple form classes')

        # We would like to helpfully complain when neither
        # of those have been filled in, but there are
        # important use cases where the set of forms is
        # constructed on the fly, either in a derived-class
        # constructor (where it would need to go between
        # the super() call and the test, above) or in the
        # prepare_request() method below (after the test
        # has been done). So we cannot test that case here.

    # basic GET handler: set up the form and
    # context and render the view
    def get(self, request, *args, **kwargs):

        # if GET has been blocked due to this being a process-
        # only form, pretend this function doesn't exist
        if self.process_only:
            return self.http_method_not_allowed(request, *args, **kwargs)
    
        # do GET/POST combined setup
        rv = self.prepare_request(*args, **kwargs)
        if isinstance(rv, self.response_base_class):
            return rv

        # prepare all the context and initial form data

        # NOTE: if a default context has been provided, it
        # must be deep-copied prior to use in case the
        # prepare_context() method needs to modify it. This
        # is inefficient if it's not going to be modified.
        if self.context is None:
            context = {}
        else:
            context = copy.deepcopy(self.context)
        initials = {}

        rv = self.prepare_all_context(context, initials)
        if isinstance(rv, self.response_base_class):
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
        rv = self.prepare_all_forms(context, initials)

        # render the template and give back a response
        return self.render(context)
        
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
        if isinstance(rv, self.response_base_class):
            return rv
        
        # figure out which form is submitted
        #
        # We do this by looking for the form_alias field
        # within the submitted data. This is complicated
        # by the fact that it, too, is probably prefixed,
        # as <form_alias>-form_alias, or it might even
        # be missing entirely.
        #
        form_alias = None
        for tested_alias in self.resolved_form_classes.iterkeys():
            if tested_alias is not None:
                alias_field = tested_alias + '-form_alias'
                if alias_field in request.POST and request.POST[alias_field] == tested_alias:
                    form_alias = tested_alias
                    break

        if form_alias is None:
            # look for an unprefixed field
            if 'form_alias' in request.POST and request.POST['form_alias'] in self.form_classes:
                form_alias = request.POST['form_alias']

        # when we're finished searching, we might still
        # be missing our alias; if we had just one form
        # without an alias, that is acceptable, but
        # otherwise, we have an error
        #
        if form_alias is None and None not in self.resolved_form_classes:
            # we're going to reject this request because
            # we don't know which form it belongs to, but
            # it's possible this is due to a programming
            # mistake like not including AjaxFormAliasMixin
            # in the form's inheritance path, so we want
            # to be more explicit in calling this out
            if settings.DEBUG:
                print 'AJAX FORM ERROR: no form_alias could be found; did you forget to derive from AjaxFormAliasMixin?'
            return self.http_method_not_allowed(request, *args, **kwargs)

        # obtain the configuration data for this form class
        form_data = self.resolved_form_classes[form_alias]
        form_attrs = form_data.get('form_attrs', {})

        if 'prefix' not in form_attrs:
            # strictly speaking, it's a bad idea to modify
            # this dict without making a copy first, because
            # the form_classes dict is usually a reference to
            # just one copy that is shared among all view
            # object instantiations; in this case, however,
            # the change would be the same every time, so
            # we will let this one slide
            form_attrs['prefix'] = form_alias

        # create the form based on the submitted data
        # (automatically pass in files if they were submitted)
        #
        # NOTE: files uploads can't be AJAX unless they use
        # the browser File API, which isn't supported in old
        # browsers; we don't handle that here, and needs to
        # be addressed in the derived class
        #
        if hasattr(request, 'FILES') and request.FILES:
            form = form_data['form_class'](request.POST, request.FILES, **form_attrs)
        else:
            form = form_data['form_class'](request.POST, **form_attrs)

        # fill in form type if specified, as a convenience
        if 'form_type' in form_data:
            form.form_type = form_data['form_type']

        rv = self.prepare_form(form, form_alias)
        if isinstance(rv, self.response_base_class):
            return rv
        
        # we may have explicitly flagged all submissions to be
        # treated as partial validation
        if self.always_partially_validate and not self.is_partial_validation:
            last_field = form.fields.keys()[-1]
            self._partial_validation_last_field = '%s-%s' % (form.prefix, last_field) if form.prefix is not None else last_field
            if settings.DEBUG:
                print 'AJAX FORM POST: forcing partial validation, ending with %s' % last_field

        if self.is_partial_validation:
            # we're only doing partial validation
            is_partially_valid = form.is_partially_valid(self._partial_validation_last_field)
            
            # call any processing needed for this partial form
            rv = self.process_partial_form(form, form_alias)
            if isinstance(rv, self.response_base_class):
                return rv
            
            # whether we are valid or not, we actually go ahead 
            # and return the form error response, so that existing
            # successfully-validated fields can be highlighted;
            # this is especially important for forms which do not
            # have submit buttons but are relying on partial
            # validation logic to do automatic submission (which
            # is a supported workflow)
            #
            # NOTE: if process_partial_form returns a dict, we will
            # assume these are additional parameters to give to
            # the AjaxFormErrorResponse constructor
            #
            if isinstance(rv, dict):
                return AjaxFormErrorResponse(form, last_field = self._partial_validation_last_field, focus_field = request.GET.get('_focus'), **rv)
            else:
                return AjaxFormErrorResponse(form, last_field = self._partial_validation_last_field, focus_field = request.GET.get('_focus'))

        else:        
            # validate the form and return an error response
            # NOTE: THIS MEANS ALL VALIDATION MUST BE DONE
            # IN THE FORM CLASS
            if not form.is_valid():
                # call any processing needed for this invalid form
                rv = self.process_invalid_form(form, form_alias)
                if isinstance(rv, self.response_base_class):
                    return rv

                # create the error response                
                if isinstance(rv, dict):
                    return AjaxFormErrorResponse(form, **rv)
                else:
                    return AjaxFormErrorResponse(form)
            
        # a valid form will usually require something to
        # be done with its data
        rv = self.process_form(form, form_alias)

        # now provide the browser with some instruction as to
        # what to do next:
        #
        # 1. Explicit instructions from process_form(). (A
        #    bare string will be interpreted as a target_url.)
        # 2. A form-specific target_url.
        # 3. A page-wide target_url.
        # 4. An AjaxResponseView-style response.
        #
        if rv is None:
            # this means use the form default target_url
            rv = form_data['target_url']
            if rv is None:
                # this means use the page-wide target_url
                rv = self.target_url

        if rv is None:
            # no JsonResponse, no target_url string...
            # fall back to AjaxResponseView-style

            # NOTE: if a default context has been provided, it
            # must be deep-copied prior to use in case the
            # prepare_context() method needs to modify it. This
            # is inefficient if it's not going to be modified.
            if self.context is None:
                context = {}
            else:
                context = copy.deepcopy(self.context)
            initials = {}

            rv = self.prepare_all_context(context, initials)
            if isinstance(rv, self.response_base_class):
                return rv

            rv = self.prepare_response(context)

        if isinstance(rv, self.response_base_class):
            # we now have a valid JSON response; stop
            return rv

        if isinstance(rv, basestring):
            # we could just overwrite self.target_url
            # but it's trivial to return the redirect
            # in one step...
            return AjaxRedirectResponse(rv)

        # we've already tested the default case (go to target_url)
        # so if we get here, our response isn't Non, a string, or
        # an HttpResponse; this is a serious programming error
        raise Exception('process_form response is not a string or HttpResponse')

    # prepare the context and initial form data for all forms
    # by letting each one process separately
    #
    # NOTE: if any form's prepare_context method returns a
    # response, it will short-circuit the entire view.
    #
    def prepare_all_context(self, context, initials):
        for form_alias,form_data in self.resolved_form_classes.iteritems():
            # extra check: sometimes we forget to include
            # AjaxFormAliasMixin for forms we want to use
            # with this view; it's not always an error if
            # the form action is directed to a single-form
            # view, but it can be helpful to flag these
            if form_data['form_class'] is None:
                raise Exception('form_class cannot be None for form_alias %s' % str(form_alias))
            if form_alias is not None and not issubclass(form_data['form_class'], AjaxFormAliasMixin) and settings.DEBUG:
                # this might be better served by simply adding the missing field
                print 'WARNING: %(form_class_name)s is not a sub-class of AjaxFormAliasMixin' % { 'form_class_name': form_data['form_class'].__name__ }

            initials[form_alias] = { 'form_alias': form_alias }
            rv = self.prepare_context(context, initials[form_alias], form_alias)
            if isinstance(rv, self.response_base_class):
                return rv

        # and the global context prep, after all the
        # forms are done
        rv = self.prepare_nonform_context(context)
        if isinstance(rv, self.response_base_class):
            return rv

    # prepare the actual form objects for all forms by
    # letting each one process separately
    #
    # NOTE: if any form's prepare_form method returns a
    # response, it will short-circuit the entire view.
    #
    def prepare_all_forms(self, context, initials):
        context['forms'] = OrderedDict()

        for form_alias,form_data in self.resolved_form_classes.iteritems():
            self.form_data = form_data              # in case handler needs it

            # extract form/helper attributes
            helper_attrs = form_data.get('helper_attrs', {})
            form_attrs = form_data.get('form_attrs', {})
            if 'prefix' not in form_attrs:
                form_attrs['prefix'] = form_alias

            # create the form object
            # NOTE: no default for form_class
            form = form_data['form_class'](initial = initials[form_alias], **form_attrs)
            context['forms'][form_alias] = form

            # fill in form type, if specified
            if 'form_type' in form_data:
                form.form_type = form_data['form_type']

            # extra step: apply Crispy helper attributes
            if hasattr(form, 'helper'):
                for k in helper_attrs:
                    setattr(form.helper, k, helper_attrs[k])

            # allow derived classes to modify the form post-creation
            rv = self.prepare_form(form, form_alias)
            if isinstance(rv, self.response_base_class):
                return rv

        # special case: for convenience, if there is just one form,
        # place it in the context
        if self.form_class is not None:
            context['form'] = context['forms'][None]

    # internally, we want to process all of our forms as though
    # multiples were provided; this property provides a wrapper
    # around this choice
    #
    # NOTE: this result is cached, so changes made after the
    # first reference will not be noticed.
    #
    @property
    def resolved_form_classes(self):
        if not hasattr(self, '_resolved_form_classes'):
            if self.form_classes is not None:
                self._resolved_form_classes = self.form_classes
            elif self.form_class is not None:
                # we have just one form class without an alias
                self._resolved_form_classes = {
                        None: {
                            'form_class': self.form_class,
                            'helper_attrs': self.helper_attrs,
                            'form_attrs': self.form_attrs,
                            'target_url': self.target_url,
                    }}
            else:
                # we have neither one nor multiple; this
                # is a configuration error
                raise ImproperlyConfigured('Must specify either a single form class or multiple form classes')

        return self._resolved_form_classes

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

