from django.http import Http404, HttpResponse
from django.template import TemplateDoesNotExist, RequestContext
from django.template.loader import get_template
from sculpt.ajax.responses import AjaxRawResponse
from sculpt.ajax.views import AjaxView
import os.path

# an AJAX-aware message view
#
# Often in our application we need to show error messages
# or other notices that are full-page items, but we also
# want to render the same messages as AJAX modals if the
# request is an AJAX request. This view will do that.
#
# YOU MUST SANITIZE URLS BEFORE FEEDING THEM TO THIS CLASS.
#
class AjaxMessageView(AjaxView):
	context = None
	template_base_path = None
	html_base_template_name = None		# base template for HTML requests
	ajax_base_template_name = None		# base template for AJAX requests

	# to force a message view to return the same
	# error code each time, you can override these
	# either in a derived class or in the urls.py
	category = None
	part1 = None
	part2 = None

	def get(self, request, category, part1, part2, *args, **kwargs):
		return self.post(request, category, part1, part2, *args, **kwargs)

	def post(self, request, category, part1, part2, *args, **kwargs):
		if self.category is not None:
			category = self.category
		if self.part1 is not None:
			part1 = self.part1
		if self.part2 is not None:
			part2 = self.part2

		return self.render_message(request, request.is_ajax(), self.context, self.template_base_path, self.html_base_template_name, self.ajax_base_template_name, category, part1, part2)

	# core message rendering piece
	#
	# pulled out into a classmethod so it
	# can (with more trouble) be invoked from
	# a function-based view
	#
	@classmethod
	def render_message(cls, request, is_ajax, context, template_base_path, html_base_template_name, ajax_base_template_name, category, part1, part2):
		# figure out which template to use
		try:
			if part2 is None:
				template = get_template(os.path.join(template_base_path, category, part1) + '.html')
			else:
				template = get_template(os.path.join(template_base_path, category, part1, part2) + '.html')
		except TemplateDoesNotExist:
			raise Http404('Unknown message page')

		# create a context for rendering
		context = RequestContext(request, context or {})
		context.update({
				'base_template_name': ajax_base_template_name if is_ajax else html_base_template_name,
			})

		# render the results
		response_text = template.render(context)
		if is_ajax:
			# we already serialized to JSON, so don't do
			# that again, but return a JsonResponse-derived
			# object so AjaxView is happy
			return AjaxRawResponse(response_text)

		else:
			return HttpResponse(response_text)


# default settings for common errors
class Ajax400MessageView(AjaxMessageView):
	category = 'error'
	part1 = 'bad-request'


class Ajax403MessageView(AjaxMessageView):
	category = 'error'
	part1 = 'forbidden'


class Ajax404MessageView(AjaxMessageView):
	category = 'error'
	part1 = 'not-found'
	

class Ajax500MessageView(AjaxMessageView):
	category = 'error'
	part1 = 'server-error'


# example urls.py fragment:
# from sculpt.ajax import messaging as messaging_views
# url(r'^(?P<category>error|message)/(?P<part1>'+SLUG_PATTERN+r')/((?P<part2>'+SLUG_PATTERN+r')/)?$', messaging_views.AjaxMessageView.as_view(
#		template_base_path = 'myapp',
# 		html_base_template_name = 'sculpt_ajax/html_message.html',
# 		ajax_base_template_name = 'sculpt_ajax/ajax_message.html',
# 	)),

# handler403 = messaging_views.Ajax403MessageView.as_view(
#		template_base_path = 'myapp',
# 		html_base_template_name = 'sculpt_ajax/html_message.html',
# 		ajax_base_template_name = 'sculpt_ajax/ajax_message.html',
# 	)
# handler404 = messaging_views.Ajax404MessageView.as_view(
#		template_base_path = 'myapp',
# 		html_base_template_name = 'sculpt_ajax/html_message.html',
# 		ajax_base_template_name = 'sculpt_ajax/ajax_message.html',
# 	)
# handler500 = messaging_views.Ajax500MessageView.as_view(
#		template_base_path = 'myapp',
# 		html_base_template_name = 'sculpt_ajax/html_message.html',
# 		ajax_base_template_name = 'sculpt_ajax/ajax_message.html',
# 	)
