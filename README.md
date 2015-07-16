sculpt-ajax
===========

This library is a set of tools, client-side and server-side, to take some of the grunt work out of integrating AJAX-y behavior into a web site.

Special Note
------------

This is not a complete project. There are no unit tests, and the only documentation is within the code itself. I don't really expect anyone else to use this code... yet. All of those things will be addressed at some point.

That said, the code _is_ being used. This started with work I did while at Caxiam (and I obtained a comprehensive license to continue with the code) so here and there are references to Caxiam that I am slowly replacing. I've done quite a bit of refactoring since then and expect to do more.

Rationale
---------

As of 2015, there are two primary approaches to dividing up the work of having a full-featured web site:

1. All of the HTML is generated by templates on the server and sent back to the client with each request. Form submissions with errors result in full new HTML pages being generated and returned. Each page URL represents a new piece of application code that must be written and generally maps to one or more functions or classes in the server application. Client-side scripting is minimal as once the pages are loaded they're mostly static. This is the "classic" model (in this context).

2. The client side is a web application, with HTML templates and fragments loaded by a client-side framework; URLs visible to the user are processed entirely within the client. The server presents a simplified API (often REST) and client-side code is fully responsible for processing data fetched from the API and formatting it for display to the user. This is the "API" model (in this context).

There are advantages and disadvantages to each model. The amount of code overall is the same; all of the code required to satisfy the project requirements has to exist _somewhere_. In the classic model, all the code resides on the server, as does all the HTML; requests to the application return HTML responses. This centralizes all the code for the application. It can (but does not have to) complicate testing of the functional pieces of the application. In the API model, the code is sharply divided: presentational code, form validation, and even portions of the business logic are moved into client-side code, and the server-side components are stripped down to the bare minimum for supporting the site. This makes the server-side components very easy to test, and has a nice side-effect of then automatically having an API that might be usable by more than the web site, but increases the complexity of building the client-side code dramatically. (Frameworks exist to reduce this burden.)

With the rise in popularity of Ember and Angular the API model is getting a lot of traction, but its requirement that large amounts of application logic be run in the client is significant. _Client-side code cannot keep secrets._ That code is open to inspection. Thus, anything that must be kept confidential has to be in server-side code. Also, a bad API design can seriously complicate building both sides of the project; while an argument can be made that creating such an API is good discipline and leads to long-term benefits to the project, it's not an easy thing to get right. In the hands of an expert the API model can be a beautiful thing.

This library exists to provide an in-between option. HTML is still generated and delivered from server-side code, but several lightweight mechanisms are provide to make routine tasks and situations more pain-free.

Features
--------

The primary benefits of using sculpt-ajax are:

* Automatic handling of failure modes that jQuery interprets as "success".
    * For example, any response with an HTTP 200 status code is considered a success, even though it might contain data about an error situation. In particular, some forms of server failure might trigger this.
* Allow server code to respond to an AJAX request by directing the browser to a completely new page.
* Automatic AJAX form validation.
    * Better error messages (not Django's default passive-aggressive ones).
    * Present a summary of errors to the user.
    * Highlight errored fields.
    * On focus, show popover with field-specific errors.
    * Easily pre- and post-process specific forms without writing lots of boilerplate.
    * TODO: add "warnings" on form validation, not just hard errors; warnings would be suppressed on second submission.
* Optional partial form validation.
    * Validate each field as it's entered, server-side, without writing special rules.
    * This can also be used to make forms "live," where data is saved without an explicit submit button.
* Optional "live" fields.
    * Data can be submitted to the server as soon as it's changed. This is a lighter-weight version of the partial form validation and live-saving options and manages just one field at a time.
* Allow server code to respond with a modal message (success and failure variants).
* Allow server code to pop "toast" (unobtrusive messages that generally disappear on their own).
* Allow server code to manipulate arbitrary parts of the DOM and replace them with new HTML fragments, append/prepend to them, or remove them entirely.
* Sensible exception handling.
    * In development mode, automatically present exceptions with backtraces in a modal. (This is redundant, since surely you'll see the backtrace in the dev server you're running locally, but it's very convenient.)
    * In non-development mode, automatically catch exceptions from views, report them via the normal Django error process with full backtrace, and respond to the user with a more polite message.
* Simple classes that abstract out most of the boilerplate of writing AJAX handlers.
    * Single or multiple forms on a single page.
    * urls.py-driven mapping of templates and views, even for partial updates.
    * Simple form-to-email and stub-JSON-response views for rapid prototyping.

