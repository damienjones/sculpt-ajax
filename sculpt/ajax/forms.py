from django import forms
from django.conf import settings
from django.utils.translation import ungettext_lazy

from sculpt.common import merge_dicts, Enumeration

import importlib

#
# forms and support code
#

# collect up all the error messages from configured modules
# and make them available for easy import
#
def collect_error_messages():
    error_messages = {}
    for module_name in settings.SCULPT_AJAX_FORM_ERROR_MESSAGES:
        m = importlib.import_module(module_name)
        merge_dicts(error_messages, m.error_messages)
    return error_messages

error_messages = collect_error_messages()

# CrispyForms mixin boilerplate
#
class CrispyMixin(object):

    def __init__(self, *args, **kwargs):
        # import here, so entire module can run without django-crispy-forms
        from crispy_forms.helper import FormHelper

        super(CrispyMixin, self).__init__(*args,**kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'id_' + (self.prefix if self.prefix else self.__class__.__name__)
        self.setup_form_helper(helper = self.helper)

    def setup_form_helper(self, helper):
        pass


# form mixin class that provides enhanced validation with two
# major new features:
#
#   1. Partial validation, so that forms can be validated
#      up to and including a specified field. This allows us
#      to immediately give a response to the user when they
#      tab out of a field whether it was valid.
#
#   2. Inter-field validation, so that rules can be written
#      to verify relationships between fields (ordering,
#      dependency, etc.).
#
#      To use inter-field validation, define a form clean
#      method and invoke the rule methods to do the
#      validation and generate appropriate error messages.
#      To override error messages, define a name for the
#      rule and include the error message in the usual
#      place.
#
#      NOTE: although inter-field validation is done AFTER
#      all single fields are validated, because the error
#      messages are added to the affected fields, they will
#      be presented in-order to the user. We tinker with
#      the messages so that it will appear after the LAST
#      affected field, not the first.
#
class EnhancedValidationMixin(object):

    # when we do partial validation, we need to record which
    # fields to accept validation messages for, so that if
    # we get a multi-field error that touches any field we
    # aren't validating, we ignore it
    _partial_validation_field_set = None
    
    # a convenient property to determine if partial validation
    # is currently being performed; if you have validation
    # rules which must only be tested on full submission
    # (e.g. username/password verification) use this to test
    # whether partial validation is being done, rather than
    # looking at _partial_validation_field_set directly
    @property
    def is_partial_validation(self):
        return self._partial_validation_field_set != None
    
    # determine whether a form is valid, up to a specific
    # field
    #
    # NOTE: this can't be a property since it requires
    # passing in the last field present
    #
    def is_partially_valid(self, last_field):
        # unbound forms are by definition without valid data
        if not self.is_bound:
            return False

        # if validation has been done then self._errors will
        # hold a dict; if it still holds None, we need to
        # perform the validation
        if self._errors == None:
            self.partially_validate(last_field)

        # if there are no errors, self._errors will be
        # truthiness False
        return not self._errors
    
    # core partial validation
    def partially_validate(self, last_field):
        
        # step 1. the last_field as given to us may be
        # prefixed, so unprefix it
        if self.prefix != None and last_field.startswith(self.prefix+'-'):
            last_field = last_field[len(self.prefix)+1:]
        
        # step 1. identify all the fields up to, and
        # including, the last field to validate
        full_field_list = self.fields.keys()
        if last_field not in full_field_list:
            # this can happen if the user is focused on a
            # submit button; rather than completely choke,
            # we just assume (perhaps erroneously) that
            # the user has completed all fields
            field_list = full_field_list
        else:
            # extract the list up to and including the
            # last field
            field_list = full_field_list[:full_field_list.index(last_field)+1]  # raises ValueError if last_field is not in the list
        
        self._partial_validation_field_set = set(field_list)
        
        # step 2. do all the validation normally
        # this will invoke the form's clean() method,
        # which may contain inter-field validation,
        # but those routines should be testing to make
        # sure errors are not added unless all affected
        # fields are present
        self.full_clean()
        
        # remove any errors which apply to fields not
        # present
        # NOTE: if the partial list in fact includes the
        # full set of fields, this loop has zero iterations
        # and all error messages are preserved
        for i in range(len(field_list), len(full_field_list)):
            field = full_field_list[i]
            if field in self._errors:
                del self._errors[field]

        # clean up the partial validation state
        self._partial_validation_field_set = None

    # a helper function that determines whether all of the
    # listed fields are valid; this basically checks to see
    # if all of the indicated keys are present in the form's
    # cleaned_data
    # (this is called internally by many of the rules)
    def are_fields_valid(self, field_list):
        for field_name in field_list:
            if field_name not in self.cleaned_data:
                return False
        return True
    
    #
    # multi-field rules
    #
    
    # require some (but not all) fields
    # expects:
    #   error_name      name to use for custom error messages;
    #                   recommended "rule<n>"
    #   field_list      list of field names
    #   min_required    minimum number of fields required;
    #                   defaults to 1
    #   max_allowed     maximum number of fields allowed;
    #                   defaults to len(field_list)
    #
    def require_fields(self, error_name, field_list, min_required, max_allowed):
        pass
        
    # require several fields to match
    def require_match(self, error_name, field_list):
        pass
        
    # require unique field values
    def require_unique(self, error_name, field_list):
        pass
        
    # core routine for require_match, require_unique:
    # require a min/max set of unique values
    def require_distinct(self, error_name, field_list, min_distinct, max_distinct, error_type = None):
        pass
        
    # ensure fields are in the correct order
    # you can write this yourself by testing fields but using
    # this ensures consistent error messages and handles
    # a LOT of cases
    #
    # NOTE: although you CAN list more than three items
    # in the field_list and enforce an ordering on all
    # of them, you should SERIOUSLY consider whether it
    # would be better to split the rule into smaller
    # groups so that it's easier for the user to spot
    # which item(s) are out of order. For example if you
    # have two sets of start/end dates, and the second
    # must start after the first ends, it may be tempting
    # to write a single rule that includes all four fields.
    # But conceptually the user thinks of these are two
    # things; each date range must be correct, AND the
    # second must start after the first ends. Split the
    # rule into three (one for each range, one to ensure
    # the second range starts after the first ends) and
    # the error messages will make more sense.
    #
    #**** TODO: allow equality of values in a controlled way
    #
    def require_ordering(self, error_name, field_list):
        pass

    # a helper function which determines if a set of fields
    # are all included in the partial validation list; this
    # can be used to identify tests which should be ignored
    # as they depend on data not present (or not expected
    # to be present) in the form data
    #
    # NOTE: this is a slightly different question from
    # whether the field is valid; this identifies whether
    # the data is expected to be present, regardless of
    # whether it has been tested and determined to be valid
    # up to this point
    #
    def are_fields_present(self, field_list):
        if self._partial_validation_field_set == None:
            # we're not in the midst of a partial validation
            # run, so all fields are expected to be present
            return True
            
        for field in field_list:
            if field not in self._partial_validation_field_set:
                return False
                
        return True        
    
    # add an error message to multiple fields at once
    def add_multiple_error_messages(self, field_list, code, params = None):
        pass


# when working with the require_ordering rule, we have the
# ability to include literals in the field list, so we need
# a way to distinguish field names from string literals;
# this class serves as a wrapper to do just that
#
# FF is mnemonic for "form field"
#
class FF(object):
    def __init__(self, field_name):
        self.field_name = field_name

# a wrapper for Django's form class that rewrites error messages
# to make them more suitable for AJAX processing; we also
# include our enhanced-validation mixin above
#
# It turns out that rewriting error messages is HARD. Django's
# process looks something like this:
#
#   full_clean
#       clean_fields            Clean each of the form fields
#                               and store any errors (simple or
#                               list) in an ErrorList
#
#           clean               Field-specific validation, most
#                               use the outline below except
#                               multi-field types. May return a
#                               list or a simple type.
#
#               to_python       Convert the string input to an
#                               appropriate Python objects. May
#                               raise a ValidationError; all Django
#                               built-in types raise error/code.
#
#               validate        Invoke the field type-specific
#                               validator and raise ValidationError
#                               in case of problems. Django's
#                               built-in types return simple
#                               error/code types. Looks for errors
#                               on the object (default is assembled
#                               from default error messages for all
#                               the classes in the hierarchy).
#
#               run_validators  Invoke individual validators and
#                               collect all the ValidationError
#                               objects into a list, then turn that
#                               into a list-style ValidationError.
#                               Catches ValidationError internally
#                               and rewrites the message if it
#                               matches one set for the field.
#   
#                   validator   Invoke the validator and raise
#                               ValidationError in case of problems.
#                               None of Django's validators raise
#                               a ValidationError with more than a
#                               simple error/code, but it's possible.
#                               Error strings generated by validators
#                               are not automatically rewritten per-
#                               field, but are done in the calling
#                               code.
#
#       clean_form              Form-wide validation code that is
#                               specific to the form. A ValidationError
#                               raised here will be placed in the
#                               __all__ bucket but will also stop
#                               additional validation taking place;
#                               more useful is to write errors into
#                               the _errors dict manually.
#
# Any of these steps may raise a ValidationError, but clean_fields
# will collect those into buckets for each specific field, and
# clean_form collects those into an __all__ bucket. All of the
# message strings are re-written with field-specific ones (even
# those raised from validators, which do not know the field context
# in which they are being used).
#
# ValidationError e gets serialized to string(s) at these times:
#
#   e.messages  converts dict/list of ValidationErroritems into
#               strings, then returns the list
#               NOTE: always returns a list, even if just one item
#
#   e.message_diict flattens nested dict/list ValidationErrors
#               into a single list per field, forcing each item
#               to string
#
# Our challenge is to rewrite the messages to be less passive-
# aggressive, including the field label in the text. To do this
# we wait until the field's error_messages dict is populated, then
# attempt to rewrite all the entries. We will throw an exception
# if we encounter a message that we do not have a replacement for.
# We must do this BEFORE any validation occurs as Django's built-
# in message rewriting for validators assumes the error messages
# are in place at that moment; once ValidationError has been
# serialized to strings it is too late for anything except the
# blunt instrument of the translation engine (which is a different
# rant, but a terrible idea).
#
# One hole is that if Django forgets to list an error message yet
# still includes the validator; this would allow the generic
# validator email message to bleed through until we found and
# fixed it.
#
# NOTE: you MUST provide a label for EVERY form field. This is
# required and this class will throw an exception if you miss one.
# The error messages cannot be rewritten properly if you do not
# do this. This applies even to fields for which the label isn't
# shown on the form.
#
# NOTE: we automatically include CrispyMixin to set up a form
# helper object without requiring extra steps. See CrispyMixin
# for more details.
#
class AjaxForm(EnhancedValidationMixin, CrispyMixin, forms.Form):

    def __init__(self, *args, **kwargs):
        # first, go ahead and let the Django Form class set
        # itself up; this loops through the field definitions
        # on the class object and creates field instances,
        # and also creates the error_messages dict for each
        # instance
        result = super(AjaxForm, self).__init__(*args, **kwargs)
        
        # now loop through the generated field list and find
        # substitute error messages for each possibility
        # NOTE: self.fields is a SortedDict, but we can iterate
        # over self like a list to retrieve the fields in order
        
        # get the error message overrides for this form
        form_specific_errors = error_messages.get(self.__class__.__name__)
        
        for name, field in self.fields.iteritems():
            # first, make sure the field has a label; this is
            # required for proper functioning of errors in the
            # client-side code
            if not hasattr(field, 'label') or field.label == "":
                raise AttributeError(
                        "Field %(name)s of type %(type)s is missing its label attribute" % {
                                'name': name,
                                'type': field.__class__.__name__
                            }
                    )

            # NOTE: we use items() instead of iteritems()
            # here because iteritems() returns an Iterator
            # which will freak out if we change the entries
            # in the dictionary while we are iterating;
            # items() makes duplicate lists and can handle
            # changing the original dictionary
            for code, message in field.error_messages.items():
                new_message = self._find_error_message(field, name, code, form_specific_errors)
                self._replace_error_message(field.error_messages, code, new_message)
        
            # extra wrinkle: some of the fields don't have
            # their own validation code, they import one or
            # more validators which themselves may raise
            # ValidationError; unfortunately Django doesn't
            # collect validation error messages from these,
            # so we look for a validators attribute and
            # process it ourselves
            if hasattr(field, 'validators'):
                for validator in field.validators:
                    if not hasattr(validator, 'code'):
                        # because there's one that doesn't, damn you Django
                        code = 'invalid'
                    else:
                        code = validator.code
                    new_message = self._find_error_message(field, name, code, form_specific_errors)
                    self._replace_error_message(field.error_messages, code, new_message)
        
        # return the original result
        return result

    # given a field, name and error code, find the appropriate
    # error message
    # NOTE: if form_specific_errors is None, it will be looked up
    # NOTE: when looking up __all__ messages, use None for field
    # NOTE: raises KeyError for undefined error messages
    @classmethod
    def _find_error_message(cls, field, field_name, code, form_specific_errors = None):
        if form_specific_errors == None:
            form_specific_errors = error_messages.get(cls.__name__)     # might still be None
            
        # for each error message, check first for a 
        # form-specific error message; if that fails,
        # walk back through the class hierarchy to see
        # if we have a replacement message, and stop at
        # the first replacement; if there are none,
        # check the _global set last

        if form_specific_errors:
            # we have form-specific errors to look through

            # form-specific field-specific
            error_id = field_name + '__' + code
            if error_id in form_specific_errors:
                return form_specific_errors[error_id]

            # form-specific form-wide
            error_id = code
            if error_id in form_specific_errors:
                return form_specific_errors[error_id]

        # no form-specific error; walk the MRO list
        # (use None as a placeholder for the classless message)
        class_name_list = [ cls.__name__ for cls in field.__class__.__mro__ ] + [ None ]
        for field_class in class_name_list:

            # what to look for for this entry
            # (usually with a class prefix)
            if field_class != None:
                error_id = field_class + '__' + code
            else:
                error_id = code

            # if we have a replacement, apply it and stop
            # searching
            if error_id in error_messages['_global']:
                return error_messages['_global'][error_id]

        # hmmm, we found an error code we can't identify;
        # treat this as an exception so that the message
        # can be added and we don't silently let this slip
        # by, uncaught
        # NOTE: DO NOT DISABLE THIS JUST TO GET YOUR CODE
        # WORKING! The correct fix is to add the error
        # message. If you disable this, you allow a bad
        # error message to slip through and be presented
        # to the end user, in a way that won't be obvious
        # and would require testing a validation failure
        # of every mode on every field type to find. (And
        # given that we're talking about an error message
        # we don't know about, that means testing a failure
        # mode we don't know about, which is kind of hard.)
        raise KeyError(
                'Unknown error message code \'%(code)s\' on field %(field)s of type %(field_class)s in form %(form)s' % {
                        'code': code,
                        'field': field_name,
                        'field_class': field.__class__.__name__,
                        'form': cls.__name__,
                    }
            )
        
    # update a set of error messages with a found message;
    # checks to see if the message is a tuple and, if so, wraps it
    # with ungettext_lazy
    @staticmethod
    def _replace_error_message(field_error_messages, code, new_message):
        if isinstance(new_message, tuple):
            field_error_messages[code] = ungettext_lazy(*new_message)
        else:
            field_error_messages[code] = new_message

    # add an error to a specific field, without having to
    # raise a ValidationError
    # Django 1.7 has something similar but it still doesn't
    # deal with replacing error messages all that well
    def add_error_message(self, field_name, code, params = None, assign_to_field = None):
        # get the field object itself, if we can
        if field_name == '__all__' or field_name == None:
            field = None
        else:
            # we can't use getattr() because this
            # bypasses the __getitem__ code that
            # gives us access to BoundField instances
            # directly off the form object; however,
            # we don't need the BoundField instance,
            # and the Field instance will do, so we
            # can go directly into the fields
            field = self.fields[field_name]
        
        # next, get the error message itself
        new_message = self._find_error_message(field, field_name, code)
        
        # if we were given parameters, expand them
        if params:
            new_message = new_message % params

        # if we should expand the field name now, do that
        # NOTE: generally we let the client side do this
        # so that it can expand it differently depending
        # on the context, but sometimes we need to create
        # an error message that refers to a different
        # field; in that case, we generate the error as
        # though it's on the original field, expand the
        # field name, and attach it to another field
        if assign_to_field == None:
            # save error to same field
            assign_to_field = field_name
        else:
            # save error to different field; expand name
            new_message = new_message.replace('__fieldname__', self.fields[field_name].label)
        
        # finally, store the message
        if assign_to_field not in self._errors:
            self._errors[assign_to_field] = self.error_class()
        self._errors[assign_to_field].append(new_message)

    # set choices onto a ChoiceField after the instance creation
    def _set_choices(self, field_name, choices):
        self.fields[field_name]._choices = choices
        # There might be a (very rare) situation where the choices are not on a widget
        # If there are choices on the widget, you have to fill the value.
        # It will cause errors with select if you don't
        if hasattr(self.fields[field_name].widget, 'choices'):
            self.fields[field_name].widget.choices = choices

# a form mix-in that automatically includes the form alias field
# so that AjaxMultiFormView can dispatch submission to the correct
# handler
class AjaxFormAliasMixin(forms.Form):
    form_alias = forms.CharField(
            label = "Form Alias",
            required = False,
            max_length = 100,
            widget = forms.HiddenInput(),
        )

