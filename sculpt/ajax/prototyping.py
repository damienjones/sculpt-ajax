from django.shortcuts import render
from sculpt.ajax.responses import AjaxSuccessResponse, AjaxErrorResponse
from sculpt.ajax.views import AjaxView, AjaxFormView

# a simple email-the-form view
#
# this is primarily useful during prototyping, to accept
# form data and send it via email somewhere
#
# NOTE: this depends on sculpt-email being available.
#
class AjaxEmailFormView(AjaxFormView):

    # pass these when you add this to urls.py
    email_address_setting = None        # settings entry that contains the email target
    email_template_name = None          # template folder for email (i.e. passed to send_mail)
    email_brand = None                  # email brand (may be left empty)
    email_from = None                   # email sender (may be left empty)

    # process the form by sending an email
    def process_form(self, request, form):
        from sculpt.email import send_mail
        send_mail(self.email_template_name, self.email_brand, getattr(settings, self.email_address_setting), self.email_from, form.cleaned_data)

# a simple prototyping view that responds to GET
# requests by rendering an HTML template and POST
# requests by rendering a JSON template.
#
class AjaxPrototypeView(AjaxView):

    # HTML template name
    template_name = None

    # JSON template name
    json_template_name = None
    
    # basic GET handler
    def get(self, request, *args, **kwargs):
        # render the template and give back a response
        return render(request, self.template_name, {})
        
    # basic POST handler: Loads the JSON and outputs the json
    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(render_to_string(self.json_template_name,{}))
            return AjaxSuccessResponse(json_data)

        except Exception as e:
            message = "There was an error with the data: " + str(e.args)
            return AjaxErrorResponse({'title': "Error", 'message': message, 'code': 1})
