from django.conf.urls import patterns, include, url

from sculpt.ajax import ajax_test

# include these in your project for testing by adding
# this to your urlpatterns:
#    url(r'ajax/', include('sculpt.ajax.test_urls')),

urlpatterns = patterns(
    url(r'^success/', ajax_test.ajax_test_success.as_view()),
    url(r'^failure/', ajax_test.ajax_test_failure.as_view()),
    url(r'^redirect/', ajax_test.ajax_test_redirect.as_view()),
    url(r'^exception/', ajax_test.ajax_test_exception.as_view()),
    url(r'^timeout/', ajax_test.ajax_test_timeout.as_view()),
    url(r'^invalid-response/', ajax_test.ajax_test_invalid_response.as_view()),
    url(r'^form/', ajax_test.ajax_test_form.as_view()),
)
