from django.conf.urls import patterns, include, url

from sculpt.ajax import ajax_test
from sculpt.ajax import messaging as messaging_views

# include these in your project for testing by adding
# this to your urlpatterns:
#    url(r'ajax/', include('sculpt.ajax.test_urls')),

SLUG_PATTERN = r'[-a-zA-Z0-9_]+'    # URL fragment for a slug

urlpatterns = patterns(
    url(r'^success/', ajax_test.ajax_test_success.as_view()),
    url(r'^failure/', ajax_test.ajax_test_failure.as_view()),
    url(r'^redirect/', ajax_test.ajax_test_redirect.as_view()),
    url(r'^exception/', ajax_test.ajax_test_exception.as_view()),
    url(r'^timeout/', ajax_test.ajax_test_timeout.as_view()),
    url(r'^invalid-response/', ajax_test.ajax_test_invalid_response.as_view()),
    url(r'^form/', ajax_test.ajax_test_form.as_view()),

	url(r'^(?P<category>error|message)/(?P<part1>'+SLUG_PATTERN+r')/((?P<part2>'+SLUG_PATTERN+r')/)?$', messaging_views.AjaxMessageView.as_view(
			template_base_path = 'sculpt_ajax',
			html_base_template_name = 'sculpt_ajax/html_message.html',
			ajax_base_template_name = 'sculpt_ajax/ajax_message.html',
		)),
)
