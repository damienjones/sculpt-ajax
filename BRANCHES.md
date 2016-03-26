# Project Branches

## Releases

### release/0.1

First public release. This is why the other sculpt-* libraries were released, so this one could be.

## Features

### feature/refactor-multiform

There are two primary views for handling forms, AjaxFormView and
AjaxMultiFormView. There is a lot of common code between them and
all too often changing one has meant changing the other as well.
This seems to be a bad pattern. Refactor these into a single view
that is capable of one or more forms, without sacrificing the easy
single-form use case.

### feature/enhanced-validation [DONE]

Build out enhanced validation methods and clean up error message
generation.

I'm closing this branch for now but I may revisit it later.

### feature/simple-messaging [DONE]

In building web sites it's often useful to have a simple way to render
a message in a template, either to a stand-alone web page or to an
error modal, without requiring separate texts for each. This feature
adds such a view and determines the context (and thus base template)
automatically.
