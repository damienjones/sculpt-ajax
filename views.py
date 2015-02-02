from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import get_template, render_to_string
from django.views.generic import View

from caxiam.ajax.responses import AjaxResponseBase, AjaxSuccessResponse, AjaxHTMLResponse, AjaxModalResponse, AjaxRedirectResponse, AjaxErrorResponse, AjaxExceptionResponse, AjaxFormErrorResponse
from caxiam.view_mixins import AjaxLoginRequiredMixin

#
# views
#

# an AJAX view base class
#
# NOTE: this derives from View, not TemplateView, because the
# default implementation for GET handling MUST be to return
# an HTTP 405 (method not supported) rather than by default
# rendering a page. This is suitable for a request which returns
# data or HTML. For a form, which renders HTML on GET and JSON
# results on POST, please use AjaxFormView instead.
#
class AjaxView(AjaxLoginRequiredMixin, View):

    # This was added so that your entire view would have access
    # to the kwargs and args, even if they aren't passed to the function
    request_kwargs = None
    request_args = None

    # by default, we do not implement GET
    
    # POST handler will be implemented by the derived view class
    
    # special handling: if an exception occurs in an AJAX POST, we
    # DO NOT want to return an exception as Django's default HTML-
    # formatted response. Instead, catch the exception and return
    # an AJAX-formatted error. However, we can't do this in a POST
    # handler because the derived class gets first crack at handling
    # it, and that's the code we need to wrap in try/except. So we
    # do the wrapping here, in dispatch.
    def dispatch(self, request, *args, **kwargs):

        self.request_kwargs = kwargs
        self.request_args = args

        # non-POST requests are not wrapped; you're on your own
        # for error handling as we assume a GET request is for the
        # form HTML
        if request.method != 'POST':
            return super(AjaxView, self).dispatch(request, *args, **kwargs)
            
        # otherwise it's a post; trap exceptions
        try:
            # spew some debug data, perhaps
            if settings.CAXIAM_AJAX_DUMP_INFO:
                if request.META.get('CONTENT_TYPE') == 'multipart/form-data':
                    # Django has already parsed the body and dumping a
                    # full uploaded file's data will not be helpful
                    print 'AJAX request:', request.META['RAW_URI'], 'MULTIPART: <file upload> +', request.POST
                else:
                    # we'd like to print the raw request if we can
                    if hasattr(request, '_body'):
                        print 'AJAX request:', request.META['RAW_URI'], 'BODY:', request._body
                    else:
                        print 'AJAX request:', request.META['RAW_URI'], 'POST', request.POST

            # call the actual POST handler
            results = super(AjaxView, self).dispatch(request, *args, **kwargs)

            if not isinstance(results, AjaxResponseBase):
                # we want to make sure all AjaxView handlers return
                # a response in the correct form; if not, we want
                # to trap those errors early in development rather
                # than let them skate by
                # NOTE: we return this rather than raise it, because
                # we don't have a backtrace (it's not helpful) and
                # because it's already formatted as an error response
                response = { 'code': 1, 'title': 'Invalid Response Type', 'message': 'Request generated an invalid response type (%s)' % results.__class__.__name__ }
                if settings.CAXIAM_AJAX_DUMP_INFO:
                    print 'AJAX result:', response
                return AjaxErrorResponse(response)

            if settings.CAXIAM_AJAX_DUMP_INFO:
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
                if settings.CAXIAM_AJAX_DUMP_INFO:
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
                if settings.CAXIAM_AJAX_DUMP_INFO:
                    print repr(response)
                return AjaxExceptionResponse(response)

    # In many AJAX requests you will need to render a set of
    # HTML fragments and return them as an AJAX HTML update
    # response. The IDs and template names need to come from
    # the urls.py but configuring individual variable names
    # for each one gets tiresome. This takes a list of
    # (id,template_name) pairs, renders them, and returns
    # them as a list of {'id':id,'html':rendered_template}
    # items suitable for passing to the AjaxHTMLResponse
    # constructor.
    #
    # NOTE: this method is deprecated for use by derived
    # classes. A better way to do this is to use the
    # AjaxMixedResponse.create() method so that you can
    # allow urls.py to set not only a list of HTML updates,
    # but also toast or modals, without changing any view
    # code.
    #
    @classmethod
    def render_html_templates(cls, context, updates):
        rendered_html = []
        for i in range(len(updates)):
            # extract data for this update
            html_id = updates[i][0]
            template_name = updates[i][1]
            if len(updates[i]) > 2:
                html_class = updates[2]
            else:
                html_class = None

            # render the update                
            template = get_template(template_name)
            html = template.render(context)
            
            # append it to the results, with class if
            # we have it
            if html_class:
                rendered_html.append({ 'id': html_id, 'html': html, 'class': html_class })
            else:
                rendered_html.append({ 'id': html_id, 'html': html })

        return rendered_html

# an AJAX template-rendering view
#
# This renders a template and returns the results in an AJAX-
# formatted wrapper that the Caxiam AJAX handler accepts.
# Use this as a drop-in replacement for TemplateView when
# making AJAX requests (but not form requests; see
# AjaxFormView below for that).
#
class AjaxTemplateView(AjaxView):
    template_name = None

    # shared setup based on request parameters;
    # if you need to validate IDs in the URL and fetch
    # records for both GET and POST, this is the place
    # to do that
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user
    def prepare_request(self, request, *args, **kwargs):
        pass

    # prep the context
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user
    def prepare_context(self, request, context):
        pass

    # shortcut to render to string using the defined template
    def render(self, request, context = None):
        if context == None:
            context = {}

        template = get_template(self.template_name)
        return template.render(RequestContext(request, context))

    # handle POST request (the normal fetch for this data)
    def post(self, request, *args, **kwargs):

        # do request setup
        rv = self.prepare_request(request, *args, **kwargs)
        if isinstance(rv, AjaxResponseBase):
            return rv

        # set up context
        context = {}
        initial = {}
        rv = self.prepare_context(request, context)
        if isinstance(rv, AjaxResponseBase):
            return rv

        # render to HTML or directly to AjaxResponseBase
        rv = self.render(request, context)
        if isinstance(rv, AjaxResponseBase):
            return rv

        return AjaxSuccessResponse(rv)

# when you are rendering HTML fragments, we want the AJAX handler
# to automatically update with the results; this is a slight
# tweak to AjaxTemplateView to automate more of it
#
class AjaxHTMLUpdateView(AjaxTemplateView):
    html_id = None      # which object in the DOM to update
    
    # override the render method to wrap it in AjaxHTMLResponse
    def render(self, request, context = None):
        html = super(AjaxHTMLUpdateView, self).render(request, context)
        
        return AjaxHTMLResponse([ { 'id': self.html_id, 'html': html }, ])

# sometimes you just want ordinary templates rendered to be
# a modal instead of results
#
class AjaxModalView(AjaxTemplateView):
    modal_title = None
    modal_code = None
    modal_size = None

    # override the render method to wrap it in AjaxHTMLResponse
    def render(self, request, context = None):
        html = super(AjaxModalView, self).render(request, context)
        
        return AjaxModalResponse(title = self.modal_title, code = self.modal_code, message = html, size = self.modal_size)

# an AJAX form view class
#
# AJAX forms return a rendered HTML page on GET but process form
# submission data on POST and return a JSON result; the Caxiam AJAX
# handler on the client will then process the errors and highlight
# the appropriate fields in the form. Successful form submission
# will direct the player to the next step.
#
# when deriving from this view, you must provide:
#   template_name   an HTML template path
#   form_class      a form class (a reference to the class,
#                   not just the name as a string)
#   target_url      where to go after the POST succeeds
#
class AjaxFormView(AjaxView):
    
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

    # shared setup based on request parameters;
    # if you need to validate IDs in the URL and fetch
    # records for both GET and POST, this is the place
    # to do that
    #
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user
    #
    def prepare_request(self, request, *args, **kwargs):
        pass

    # prep the context and initial form data
    #
    # NOTE: you don't have to put form into context, the
    # boilerplate will do that
    #
    # NOTE: this IS NOT called for POST because POST
    # will not render HTML
    #
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user
    #
    def prepare_context(self, request, context, initial):
        pass

    # after the form object has been created, it may
    # need to be modified before being rendered or
    # validated; do that here
    #
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user
    #
    def prepare_form(self, request, form):
        pass

    # when a form has been successfully validated, do
    # something with the data; this is the most important
    # function to override and will typically save the
    # data or at least update target_url
    #
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user;
    # you may also return a string to indicate a
    # different target URL than the default
    #
    def process_form(self, request, form):
        pass
    
    # when a form is being partially validated you may
    # want to do something (and usually this is very
    # different from what you do with a fully-valid form)
    #
    def process_partial_form(self, request, form):
        pass
    
    #
    # boilerplate, so you don't have to keep writing it
    #
    
    # basic GET handler: set up the form and
    # context and render the view
    def get(self, request, *args, **kwargs):

        # do GET/POST combined setup
        rv = self.prepare_request(request, *args, **kwargs)
        if isinstance(rv, (HttpResponse)):
            return rv
        
        # set up context and initial form data
        context = {}
        initial = {}
        rv = self.prepare_context(request, context, initial)
        if isinstance(rv, (HttpResponse)):
            return rv

        # create form(s) and give the derived class a chance
        # to modify it
        form = self.form_class(initial = initial, **self.form_attrs)
        context['form'] = form

        # Allows you to prepopulate the helper attributes before you prepare the form
        for k in self.helper_attrs:
            setattr(form.helper, k, self.helper_attrs[k])

        rv = self.prepare_form(request, form)
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
        rv = self.prepare_request(request, *args, **kwargs)
        if isinstance(rv, AjaxResponseBase):
            return rv
        
        # create the form based on the submitted data
        # (automatically pass in files if they were submitted)
        if hasattr(request, 'FILES') and request.FILES:
            form = self.form_class(request.POST, request.FILES, **self.form_attrs)
        else:
            form = self.form_class(request.POST, **self.form_attrs)
        rv = self.prepare_form(request, form)
        if isinstance(rv, AjaxResponseBase):
            return rv
        
        if self.is_partial_validation:
            # we're only doing partial validation
            is_partially_valid = form.is_partially_valid(self._partial_validation_last_field)
            
            # call any processing needed for this partial form
            rv = self.process_partial_form(request, form)
            if isinstance(rv, AjaxResponseBase):
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
        rv = self.process_form(request, form)
        if isinstance(rv, AjaxResponseBase):
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
    # by returning AjaxResponse objects
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

    # shared setup based on request parameters;
    # if you need to validate IDs in the URL and fetch
    # records for both GET and POST, this is the place
    # to do that
    #
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user
    #
    def prepare_request(self, request, *args, **kwargs):
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
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user,
    # aborting all other form processing
    #
    def prepare_context(self, request, context, initial, form_alias):
        method_name = 'prepare_context_%s' % form_alias
        if form_alias in self.form_classes and hasattr(self, method_name) and callable(getattr(self, method_name)):
            return getattr(self, method_name)(request, context, initial)

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
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user,
    # aborting all other form processing
    #
    def prepare_form(self, request, form, form_alias):
        method_name = 'prepare_form_%s' % form_alias
        if form_alias in self.form_classes and hasattr(self, method_name) and callable(getattr(self, method_name)):
            return getattr(self, method_name)(request, form)

    # when a form has been successfully validated, do
    # something with the data; this is the most important
    # function to override and will typically save the
    # data or at least update target_url
    #
    # NOTE: you probably don't want to override this,
    # but provide process_form_<alias> instead
    #
    # NOTE: a normal return value should be None, but
    # if you return an AjaxResponseBase type, processing
    # will stop and that response sent back to the user;
    # you may also return a string to indicate a
    # different target URL than the default
    #
    def process_form(self, request, form, form_alias):
        method_name = 'process_form_%s' % form_alias
        if form_alias in self.form_classes and hasattr(self, method_name) and callable(getattr(self, method_name)):
            return getattr(self, method_name)(request, form)
    
    # similarly, if you want to process partial form
    # data, provide a process_partial_form_<alias>
    # method; if it returns an AjaxResponse object,
    # that will be given to the browser
    #
    # the notes on process_form apply to this as well
    #
    def process_partial_form(self, request, form, form_alias):
        method_name = 'process_partial_form_%s' % form_alias
        if form_alias in self.form_classes and hasattr(self, method_name) and callable(getattr(self, method_name)):
            return getattr(self, method_name)(request, form)
    
    #
    # boilerplate, so you don't have to keep writing it
    #
    
    # basic GET handler: set up the form and
    # context and render the view
    def get(self, request, *args, **kwargs):

        # do GET/POST combined setup
        rv = self.prepare_request(request, *args, **kwargs)
        if isinstance(rv, AjaxResponseBase):
            return rv
        
        # set up context and initial form data
        context = {}
        initials = {}
        for form_alias,form_data in self.form_classes.iteritems():
            form_class, helper_attrs, target_url = form_data
            initials[form_alias] = { 'form_alias': form_alias }
            rv = self.prepare_context(request, context, initials[form_alias], form_alias)
            if isinstance(rv, AjaxResponseBase):
                return rv

        # create form(s) and give the derived class a chance
        # to modify it
        context['forms'] = {}
        for form_alias,form_data in self.form_classes.iteritems():
            form_class, helper_attrs, target_url = form_data
            if helper_attrs == None:
                helper_attrs = {}
            form_attrs = {}
            if len(form_data) > 3:
                form_attrs = form_data[3]
            if 'prefix' not in form_attrs:
                form_attrs['prefix'] = form_alias
            form = form_class(initial = initials[form_alias], **form_attrs)
            context['forms'][form_alias] = form

            # extra step: apply Crispy helper attributes
            for k in helper_attrs:
                setattr(form.helper, k, helper_attrs[k])

            rv = self.prepare_form(request, form, form_alias)
            if isinstance(rv, AjaxResponseBase):
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
        rv = self.prepare_request(request, *args, **kwargs)
        if isinstance(rv, AjaxResponseBase):
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
                return self.http_method_not_allowed(request, *args, **kwargs)
            form_alias = request.POST['form_alias']

        form_data = self.form_classes[form_alias]
        form_class, helper_attrs, target_url = form_data
        if target_url == None:
            # this form doesn't have a specific target URL;
            # use the class-wide one
            target_url = self.target_url
        form_attrs = {}
        if len(form_data) > 3:
            form_attrs = form_data[3]
        if 'prefix' not in form_attrs:
            form_attrs['prefix'] = form_alias

        # create the form based on the submitted data
        form = form_class(request.POST, **form_attrs)
        rv = self.prepare_form(request, form, form_alias)
        if isinstance(rv, AjaxResponseBase):
            return rv
        
        if self.is_partial_validation:
            # we're only doing partial validation
            is_partially_valid = form.is_partially_valid(self._partial_validation_last_field)
            
            # call any processing needed for this partial form
            rv = self.process_partial_form(request, form, form_alias)
            if isinstance(rv, AjaxResponseBase):
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
        rv = self.process_form(request, form, form_alias)
        if isinstance(rv, AjaxResponseBase):
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
    
