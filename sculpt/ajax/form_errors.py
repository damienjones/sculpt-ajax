# form validation error messages
#
# included as a separate file so that they are easily modifiable
# by people who are not necessarily Python experts; it also makes
# it very easy to replace and/or translate
#
# Django's suggestion of abusing the translation system just to
# sub in different error messages is as idiotic as their isolation
# of validation error texts from the context in which they are
# applied.
#
# When writing error messages, do not use passive-aggressive
# language; be clear and direct without being insulting or snide.
# Each error message should include __fieldname__ as the
# placeholder for the field name; this won't be replaced by Django,
# but rather by client-side JavaScript code. Some error messages
# may have other placeholders that are filled in with data from the
# validator on the server side.
#
# Some messages are given as a tuple instead of as a single string.
# These are handed off to ungettext_lazy once the value is known
# for pluralization. Not ideal, but acceptable.
#
# Within each grouping, PLEASE keep the list alphabetized by name.
# This will make finding and verifying entries easier without risk
# of missing duplicate entries.

error_messages = {
        # error messages that apply to all form classes
        # for each entry, use fieldclassname__errorcode (applies to that field class)
        # or just errorcode (applies to any class)
        '_global': {
                # error messages that are not type-specific
                'min_length': '__fieldname__ must be at least %(limit_value)d characters; you entered %(show_value)d.',     # technically 1 is possible but if you need that, just make it required
                'min_value': '__fieldname__ must be at least %(limit_value)s.',
                'max_length': (
                        '__fieldname__ must be no more than one character; you entered %(show_value)d.',
                        '__fieldname__ must be no more than %(limit_value)d characters; you entered %(show_value)d.',
                        'limit_value',
                    ),
                'max_value': '__fieldname__ must be no more than %(limit_value)s.',
                'required': '__fieldname__ is required.',
                
                'nomatch': '%(fieldname1)s and %(fieldname2)s must match.',
                
                # type-specific error messages
                'ChoiceField__invalid_choice': '__fieldname__ does not have a valid choice.',       # Django's version of this message echoes back the user selection. We decline. This error shouldn't happen anyway (choice fields use drop-downs...)
                'DateField__invalid': '__fieldname__ must be a valid date.',
                'DateTimeField__invalid': '__fieldname__ must be a valid date and time.',
                'DecimalField__invalid': '__fieldname__ must be a number.',
                'DecimalField__max_decimal_places': (
                        '__fieldname__ must have no more than one decimal place.',
                        '__fieldname__ must have no more than %(max)s decimal places.',
                        'max',
                    ),
                'DecimalField__max_digits': (                                       # you probably wanted max_decimal_places and max_whole_digits instead
                        '__fieldname__ must have no more than one digit.',
                        '__fieldname__ must have no more than %(max)s digits.',
                        'max',
                    ),
                'DecimalField__max_whole_digits': (
                        '__fieldname__ must have no more than one digit before the decimal point.',
                        '__fieldname__ must have no more than %(max)s digits before the decimal point.',
                    ),
                'EmailField__invalid': '__fieldname__ must be a valid email address.',
                'FileField__contradiction': '__fieldname__ should either contain a file or the &#8220;clear&#8221; checkbox should be checked, not both.',  # ...yeuch...
                'FileField__empty': '__fieldname__ had a file included, but the file was empty.',
                'FileField__invalid': '__fieldname__ did not contain a file. Check the encoding type on the form.',
                'FileField__max_length': '__fieldname__&#8217;s file has a long name (%(length)d characters); it must be no more than %(max)d characters.', # technically 1 is possible but don't do that
                'FileField__missing': '__fieldname__ did not contain a file.',
                'FloatField__invalid': '__fieldname__ must be a number.',
                'ImageField__invalid_image': '__fieldname__ must be a valid image file. This one is either corrupt, or not an image file.',
                'IntegerField__invalid': '__fieldname__ must be a whole number.',   # technically inaccurate, but 'integer' is jargon and 'whole number' is what makes sense to most people.
                'IntegerListField__invalid': '__fieldname__ contains one or more invalid entries: %(invalid_entries)s',    # really should not be shown to the user
                'IPAddressField__invalid': '__fieldname__ must be a valid IPv4 address.',           # 'IPv4' is jargon, but anyone being asked to enter a bare IP address should know what that is
                'MultipleChoiceField__invalid_choice': '__fieldname__ has an invalid choice.',      # Django's version of this message echoes back the user selection. We decline. This error shouldn't happen anyway (choice fields use drop-downs...)
                'MultipleChoiceField__invalid_list': '__fieldname__ must be a list of values.',     # this should never appear; it should be a smart widget
                'MultiValueField__invalid_list': '__fieldname__ must be a list of values.',         # this should never appear; it should be a smart widget
                #'RegexField__invalid': '__fieldname__ must be valid.',                             # explicitly disabled; do not derive from RegexField without defining this value
                'SlugField__invalid': '__fieldname__ must be a valid &#8220;slug&#8221;, consisting only of letters, numbers, hyphens, or underscores.',
                'SplitDateTimeField__invalid_date': '__fieldname__ must have a valid date.',
                'SplitDateTimeField__invalid_time': '__fieldname__ must have a valid time.',
                'TimeField__invalid': '__fieldname__ must be a valid time.',
                'URLField__invalid': '__fieldname__ must be a valid URL.',
                
                # The GenericIPAddressField actually changes which validator it applies based on
                # the supported protocol(s) indicated in its constructor; unfortunately, ALL of
                # the available validators use code 'invalid', so after the fact it's impossible
                # to tell WHICH error message might be returned without specific code to test
                # for these differences. Stupid, stupid, stupid. We replace the default case
                # (both) and recommend using IPAddressField for IPv4-only validation, and writing
                # an IPv6-only wrapper on GenericIPAddressField if you need such a thing.
                'GenericIPAddressField__invalid': '__fieldname__ must be a valid IPv4 or IPv6 address.',
            },

        # error messages that are specific to an individual
        # form class; use the class name as the key
        # NOTE: unlike _global, we prefix items here with
        # the fieldname__ instead of fieldclassname__
        # NOTE: both flavors are checked here before _global

        # here is an example:

        # 'AppAuthenticationForm': {
        #         # these are left as form-wide as they are applied to both username and password
        #         'inactive': 'This account is inactive and cannot be used.',
        #         'invalid_login': 'This username and pasword do not match our records. Note that passwords are case-sensitive.',
        #     },
    }
