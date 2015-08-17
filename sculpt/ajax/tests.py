from django import forms
from django.test import SimpleTestCase
from sculpt.ajax.forms import AjaxForm

# tests
#
# not because we particularly love taking tests, but
# because we need to be reasonably certain this stuff
# works as advertised, even when we change things

# we need an example form, so we create one that
# contains just about every known type of field
class AjaxFormTestForm(AjaxForm):

    bool1 = forms.BooleanField(label = 'BoolField1', required = False)
    char1 = forms.CharField(label = 'CharField1', required = False, max_length = 20)
    char2 = forms.CharField(label = 'CharField2', required = False, max_length = 10)
    char3 = forms.CharField(label = 'CharField3', required = False, max_length = 10)
    choices1 = forms.ChoiceField(label = 'ChoicesField1', required = False, choices = (('0','option1'),('1','option2'),('2','option3')))
    typedchoices1 = forms.TypedChoiceField(label = 'TypedChoices1', required = False, choices = ((0,'integer0'),(1,'integer1'),(2,'integer2')), coerce = int)
    date1 = forms.DateField(label = 'DateField1', required = False)
    date2 = forms.DateField(label = 'DateField2', required = False)
    date3 = forms.DateField(label = 'DateField3', required = False)
    datetime1 = forms.DateTimeField(label = 'DateTimeField1', required = False)
    datetime2 = forms.DateTimeField(label = 'DateTimeField2', required = False)
    decimal1 = forms.DecimalField(label = 'DecimalField1', required = False, max_digits = 6, decimal_places = 2)
    decimal2 = forms.DecimalField(label = 'DecimalField2', required = False, max_digits = 6, decimal_places = 2)
    email1 = forms.EmailField(label = 'EmailField1', required = False)
    float1 = forms.FloatField(label = 'FloatField1', required = False)
    float2 = forms.FloatField(label = 'FloatField2', required = False)
    integer1 = forms.IntegerField(label = 'IntegerField1', required = False)
    integer2 = forms.IntegerField(label = 'IntegerField2', required = False)
    ipaddress1 = forms.GenericIPAddressField(label = 'GenericIPAddressField1', required = False)
    multiplechoice1 = forms.MultipleChoiceField(label = 'MultipleChoiceField1', required = False, choices = (('0','option1'),('1','option2'),('2','option3')))
    typedmultiplechoice1 = forms.TypedMultipleChoiceField(label = 'TypedMultipleChoiceField1', required = False, choices = ((0,'integer0'),(1,'integer1'),(2,'integer2')), coerce = int)
    nullbool1 = forms.NullBooleanField(label = 'NullBooleanField1', required = False)
    #regex1 = forms.RegexField(label = 'RegexField1', required = False, regex = r'^a.*k$', error_messages = { 'invalid': '__fieldname__ must be a string that starts with "a" and ends with "k".' })
    slug1 = forms.SlugField(label = 'SlugField1', required = False)
    slug2 = forms.SlugField(label = 'SlugField2', required = False)
    time1 = forms.TimeField(label = 'TimeField1', required = False)
    time2 = forms.TimeField(label = 'TimeField2', required = False)
    url1 = forms.URLField(label = 'URLField1', required = False)
    #**** TODO: MultiValueField

    def clean(self):
        self.require_fields('rule1', [ 'char1', 'date1', 'email1', 'integer1' ], min_required = 1, max_allowed = 3)
        self.require_match('rule2', [ 'slug1', 'slug2' ])
        self.require_unique('rule3', [ 'char1', 'char2', 'char3' ])
        self.require_ordering('rule4', [ 'date1', 'date2', 'date3' ], allow_equality_positions = [ 0, 1 ])
        self.require_ordering('rule5', [ 'datetime1', 'datetime2' ])
        self.require_ordering('rule6', [ 'time1', 'time2' ])
        self.require_ordering('rule7', [ 'integer1', 'integer2' ], allow_equality_positions = [ 0 ])

class AjaxFormTestCase(SimpleTestCase):

    def test_error_message_replacement(self):
        # should not generate an exception
        form = AjaxFormTestForm()

    def test_require_fields_min_required(self):
        # no fields submitted
        form_data = {
        }
        form = AjaxFormTestForm(form_data)
        self.assertEqual(form.is_valid(), False)    # should not be valid
        self.assertIsNotNone(form._errors)          # should have errors
        self.assertIn('char1', form._errors)        # these fields should be marked with errors due to require_fields
        self.assertIn('date1', form._errors)
        self.assertIn('email1', form._errors)
        self.assertIn('integer1', form._errors)
        self.assertIn('CharField1, DateField1, EmailField1 and IntegerField1', form._errors['char1'][0])  # full field list should be in error

    def test_require_fields_max_allowed(self):
        form_data = {
            'char1': 'abcdef',
            'date1': '1/1/2001',
            'email1': 'foo@foo.com',
            'integer1': '2',
        }
        form = AjaxFormTestForm(form_data)
        self.assertEqual(form.is_valid(), False)    # should not be valid
        self.assertIsNotNone(form._errors)          # should have errors
        self.assertIn('char1', form._errors)        # these fields should be marked with errors
        self.assertIn('date1', form._errors)
        self.assertIn('email1', form._errors)
        self.assertIn('integer1', form._errors)
        self.assertIn('CharField1, DateField1, EmailField1 and IntegerField1', form._errors['char1'][0])  # full field list should be in error

    def test_require_fields_valid(self):
        form_data = {
            'char1': 'abcdef',
            'date1': '1/1/2001',
            'email1': 'foo@foo.com',
        }
        form = AjaxFormTestForm(form_data)
        self.assertEqual(form.is_valid(), True)     # should not be valid
