from django.shortcuts import render
from sculpt.ajax.responses import AjaxSuccessResponse, AjaxErrorResponse
from sculpt.ajax.views import AjaxView, AjaxFormView
from sculpt.email import send_mail

# a simple email-the-form view
#
# this is primarily useful during prototyping, to accept
# form data and send it via email somewhere
#
class AjaxEmailFormView(AjaxFormView):

    # pass these when you add this to urls.py
    email_address_setting = None        # settings entry that contains the email target
    email_template_name = None          # template folder for email (i.e. passed to send_mail)
    email_brand = None                  # email brand (may be left empty)
    email_from = None                   # email sender (may be left empty)

    # process the form by sending an email
    def process_form(self, request, form):
        send_mail(self.email_template_name, self.email_brand, getattr(settings, self.email_address_setting), self.email_from, form.cleaned_data)

# This is used for Blake's prototyping.  This allows him to make complete
# prototypes with (semi) working ajax.  He can completely write ALL of the
# front end and submit the ajax to a real url that would give him data back
# NOTE: THIS DOES NOT EMPOWER BLAKE TO BE THE END ALL BE ALL FOR DATA DESIGN
# NOTE: IF IN THE FUTURE, THE JSON STRUCTURE HAS CHANGED, THEN EITHER THE DEV
#    OR THE FRONT END DEV HAS TO MAKE THE CHANGES TO THE JS.
class AjaxPrototypeView(AjaxView):
    # these attributes must be present (but unfilled) or the
    # as_view method will not allow them to be set
    template_name = None

    # Blake needs to be able to add a pointer to a file filled
    # with preformatted json data.  This controller is used
    # specifically for prototyping for use without the intervention
    # of a Python Developer
    json_file_name = None
    
    # basic GET handler
    def get(self, request, *args, **kwargs):
        # render the template and give back a response
        return render(request, self.template_name, {})
        
    # basic POST handler: Loads the JSON and outputs the json
    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(render_to_string(self.json_file_name,{}))
            # default handling is to go to the target URL
            return AjaxSuccessResponse(json_data)
        except Exception as e:
            message = "There was an error with the data: " + str(e.args)
            return AjaxErrorResponse({'title':"Error", 'message':message, 'code': 1})
