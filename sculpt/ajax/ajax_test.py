from django import forms
from django.shortcuts import render
from sculpt.ajax.forms import AjaxForm
from sculpt.ajax.responses import AjaxFormErrorResponse, AjaxRedirectResponse, AjaxErrorResponse, AjaxSuccessResponse
from sculpt.ajax.views import AjaxView, AjaxFormView
import time

class ajax_test_success(AjaxView):

    def post(self, request, *args, **kwargs):
        return AjaxSuccessResponse({ 'foo': 'bar' })
        
class ajax_test_failure(AjaxView):

    def post(self, request, *args, **kwargs):
        return AjaxErrorResponse({ 'code': 2, 'title': 'Test Error', 'message': 'This test is a "success" by being a failure.' })
        
class ajax_test_redirect(AjaxView):

    def post(self, request, *args, **kwargs):
        return AjaxRedirectResponse('/')
        
class ajax_test_exception(AjaxView):

    def post(self, request, *args, **kwargs):
        raise Exception('this exception should be returned as a JSON-parseable response')

class ajax_test_timeout(AjaxView):

    def post(self, request, *args, **kwargs):
        time.sleep(45)
        raise Exception('this request should have timed out before this')

class ajax_test_invalid_response(AjaxView):

    def post(self, request, *args, **kwargs):
        return 'This is a plain-text (invalid type) response.'

class ajax_test_form_form(AjaxForm):

    from_address = forms.CharField(label = 'From', required = True, max_length = 10)
    message = forms.CharField(label = 'Message', required = True, widget = forms.Textarea)

#class ajax_test_form(AjaxFormView):
#    template = "introtome/ajax_form_test.html"
#    form_class = ajax_test_form_form
#
#    def get(self, request, *args, **kwargs):
#        form = self.form_class()
#        context = {
#                'form': form,
#            }
#        return render(request, self.template, context)
#
#    def post(self, request, *args, **kwargs):
#        form = self.form_class(request.POST)
#        if form.is_valid():
#            return AjaxRedirectResponse('/')
#        else:
#            return AjaxFormErrorResponse(form)

class ajax_test_form(AjaxFormView):
    template = "introtome/ajax_form_test.html"
    form_class = ajax_test_form_form
    target_url = '/'
