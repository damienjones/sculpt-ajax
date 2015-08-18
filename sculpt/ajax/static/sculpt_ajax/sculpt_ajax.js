// Code Sculpture AJAX handler
//
// Generally speaking, this relies on both jQuery and
// Bootstrap for its modals and tooltips. If you're not
// using Bootstrap, anything that supplies equivalent
// invocations (e.g. sculpt-transient) will work, too.

;var Sculpt = (function ($, undefined) {
	return {
		// for initialization, see the BOTTOM of this class

		// default settings
		'default_modal_size': 'small',		// for server-generated error modals
		'last_modal_result': null,			// last-processed modal result value
		'default_formerror_modal_size': 'medium',	// only for form errors, which are often bigger
		'auto_form_handlers': {},			// any registered automatic form handlers
		'upload_queue': [],					// any collected uploadable files
		'upload_queue_id': 1,				// ID of next queue item (so we never duplicate an HTML ID)
		'chosen_selector': 'select',		// selector to use to turn things into chosen selects

		// internal tracking flags
		'_skip_partial_validation': null,	// gets set to form name that should be skipped for partial validation because it was submitted

		// special classes
		//
		// _sculpt_no_ajax - disables AJAX form handling for this form
		// _sculpt_ajax_partial - enable partial form validation for this form
		// _sculpt_ajax_autoclose - close modal containing form on success
		// _sculpt_ajax_autoclear - clear form on success
		// _sculpt_ajax_upload - form contains upload field
		// _sculpt_ajax_live - field is live-updated to the server; requires extra attributes
		// _sculpt_ajax_post - if added to links, forces them to AJAX POST (supports responses)
		// _sculpt_modal_dismiss - if added to links, forces modal to close first (_sculpt_ajax_post required)
		// _sculpt_decorative - if added to links, swallows clicks (useful for prototyping)

		'ajax': function (opts, success, failure, show_busy, fail_silently) {
			//
			// Core AJAX handler
			//
			// We submit AJAX requests as POST (always) and examine the results to decide
			// what to do. There are several possibilities:
			//
			// 1. The request could time out.
			//
			//    The server might be offline, the internet connection might have broken,
			//    or the request is just taking too long. Show an error to the user,
			//    then invoke the failure handler on the AJAX request.
			//
			// 2. The server could return an error.
			//
			//    Such a response will not have a JSON-parseable body. It might be a
			//    server error (500) or a 400-range error; we should display an error to
			//    the user indicating such, then invoke the failure handler on the
			//    AJAX request.
			//
			//    NOTE: we will never directly receive a 301/302 response to an AJAX
			//    call. The browser will internally follow the redirect before we even
			//    see it. Therefore, responses which are intended to redirect the host
			//    page return a JSON-formatted response which we interpret below.
			//
			// 3. The server could return a successful response that does not parse as
			//    valid JSON.
			//
			//    This is a degenerate case and should never happen from our application
			//    code; however, we are human and mistakes happen. We treat this as a
			//    server error and display a response to the user, then invoke the failure
			//    handler on the AJAX request.
			//
			// 4. The server could return a JSON-parseable response. Hooray.
			//
			// 4a. The response indicates a host page redirect. Do it. (See note on #2.)
			//
			//     NOTE: we do not invoke EITHER the success or failure handlers on the
			//     AJAX request; we interpret this server-designated redirect as an
			//     instruction to completely dump JavaScript state and move to a new
			//     page without delay.
			//
			// 4b. The response indicates an exception.
			//
			//	   When the server is in a DEBUG configuration, exceptions will be
			//	   given with backtraces and these should be presented. Otherwise,
			//	   a generic message should be shown to the user as the server will
			//	   not be providing details.
			//
			//     Show the error to the user, then invoke the failure handler on the
			//     AJAX request.
			//
			// 4c. The response indicates a form validation error.
			//
			//     This should only happen on a form submission. Show the errors to the
			//     user and highlight the form fields appropriately, then invoke the
			//     failure handler on the AJAX request.
			//
			//     In some cases we might want to return a completely different error
			//     message to the user (like 4d, below) but still treat the result as
			//     a form error to retain its field highlighting and error popover
			//     capabilities. We thus also check for such a specific error message
			//     and, if present, show that in place of our generated-from-field-
			//     errors message.
			//
			//     NOTE: normally a failure handler is not needed in this case because
			//     we have already shown the error to the user. Only use the error
			//     handler if there is special processing that you need to do.
			//
			// 4d. The response indicates a processing error.
			//
			//     This indicates an expected error such as "login required" or
			//	   "permission denied". Some of these could certainly have been
			//	   implemented with HTTP response codes, but by handling them this
			//	   way we allow the server to return specific error text for the
			//	   request, rather than more generic text.
			//
			//     Show the error to the user, then invoke the failure handler on the
			//     AJAX request.
			//
			// 5.  The response indicates success. Double Hooray.
			//
			//     The server may indicate one OR MORE of the following successful
			//     responses:
			//
			// 5a. Request-specific data.
			//
			//     Since this is request/application-specific, if this kind of result
			//     is detected, we invoke the success handler immediately and do not
			//     do any further processing, even if HTML, modal, or toast results
			//     are present. This way, the application can easily disable the
			//     processing of these results.
			//
			// 5b. HTML results.
			//
			//     This is given as a list of element IDs and the HTML to overwrite
			//     their contents with. We automate this because it's such a common
			//     operation. The success handler is invoked, but not until modal
			//     or toast requests are processed.
			//
			// 5c. The response requires toast.
			//
			//     Toast is a modeless notice that typically pops up from the bottom
			//     of the browser window and disappears on its own after a set amount
			//     of time. It is ideal for short confirmation messages that do not
			//     require interrupting the user's task, such as when saves are
			//     incremental or the user is expected to immediately enter a new
			//     record. The success handler is invoked, but not until modal
			//     requests are processed.
			//
			//     NOTE: toast triggered by this mechanism cannot have any callbacks
			//     attached. If callbacks are required when toast is delivered or
			//     removed, return results and invoke toast from a success handler.
			//
			// 5d. The response requires a modal notice.
			//
			//     This visually looks similar to a processing error (case 4c) but
			//     it's treated as a successful response and there is an opportunity
			//     to style the modal differently. The success handler is invoked,
			//     but not until the modal is closed by the user.
			//
			//     NOTE: a successful form submission will usually not return any
			//     type 5 kind of response, but will instead return a 4a redirect
			//     response to take the user to a new page. However in some cases it
			//     may make sense to incrementally build a page while maintaining
			//     state in the user's session.
			//
			// 6.  The response, which is JSON-parseable, doesn't seem to have any of
			//     our required instructions.
			//
			//     This is a programming screw-up. Show an error to the user and invoke
			//     the failure handler on the AJAX request.
			//
			// TIMEOUT NOTE: the timer starts as soon as the AJAX request is queued,
			// but browsers will limit the number of simultaneous connections to a single
			// server and if a lot of AJAX requests are pending, a request may time out
			// on the client side before it is even submitted to the server. For this
			// reason we set the limit relatively high by default, longer than we would
			// comfortably use as a server setting.
			//
			// CALLBACK NOTE: in contrast to the jQuery success/failure callbacks, we
			// use a single parameter signature for these callbacks which allows you to
			// use the same function for each if you want. We pass:
			//
			//	callback(success, data, status, message, jqXHR)
			//
			//		success: false for ALL failure modes
			//		data: an object for success; for errors, may be an object or null
			//		status:
			// success will be true or false. data will be null on failure. message will
			// be null on success.
			//
			// RETURN VALUE NOTE: This call returns the jqXHR object which is derived
			// from Deferred, so you may be tempted to use the .done and .fail methods
			// to attach handlers. DO NOT DO THIS. "Success" and "failure" of the
			// underlying AJAX request is not sufficient, as many "success" modes are
			// still failures. Use the success and failure parameters instead. Later
			// we may refactor to return a Deferred object of our own. The primary
			// reason for returning the jqXHR is to allow upload progress monitoring.
			// This is now irrelevant as we do file upload monitoring internally.
			//
			// Zach Stevenson 7/10/2014  Added a flag to fail silently.  There are situations
			// like predictive search when you are doing abort() on the ajax object when you
			// don't want it to pop up a modal saying "You canceled the operation".
			// By marking this you know that you are risking possibly unexpected behaviour.

			// convenience option: if opts is just a string, treat it as
			// the URL
			if (typeof(opts) == 'string')
				opts = { url: opts };

			// overlay call-specific options onto our defaults
			var new_opts = $.extend({}, {
				accepts: 'application/json',
				async: true,
				dataType: 'json',			// jQuery should infer this from the response MIME type
				timeout: 30000,				// timeout, in milliseconds; see above for notes on timeout
				type: 'POST'				// DO NOT override this* (*unless you're an expert)
			}, opts);

			// special check: if this request is back to the same domain, include the
			// Django CSRF token (else our request will be denied)
			//
			// NOTE: we check for this by looking for an explicit http: or https prefix
			// on the request, on the assumption that ALL local requests will omit
			// this; if your AJAX requests are returned with 403, you might be making
			// a fully-qualified request which won't work (and is bad anyway because
			// then your code can't be repointed based on deployment environment).
			// This probably would be rejected anyway based on the browser's same-
			// origin policy.
			//
			// NOTE: if we don't have a CSRF token already fetched, this won't work
			// either; make sure you've invoked Sculpt.extract_cookies() at least
			// once after page load. Alternatively, make sure you're POSTing a form
			// that includes the CSRF token.
			//
			if (!new_opts.url.match(/^https?:/i) && this.cookies && this.cookies.csrftoken)
			{
				if (typeof(new_opts.headers) == 'undefined')	// create a headers setting if none defined
					new_opts.headers = {};
				new_opts.headers['X-CSRFToken'] = this.cookies.csrftoken;
			}

			// if we are going to show a "busy" indicator, it would go here

			// make the request
			var jqXHR = $.ajax(new_opts);

			// set up the callbacks; we do this here because
			// we are going to pass in the given callbacks
			var that = this;				// the inline functions below run with a different "this" context, so alias it
			jqXHR.done(function(data, status, jqXHR) {
				return that._ajax_success(success, failure, fail_silently, show_busy, data, status, jqXHR);
			}).fail(function(jqXHR, status, message) {
				return that._ajax_failure(success, failure, fail_silently, show_busy, jqXHR, status, message);
			});

			return jqXHR;
		},

		// whenever an AJAX method "succeeds", this is called; this includes
		// all cases in types 4, 5, and 6 defined above
		'_ajax_success': function (success, failure, fail_silently, show_busy, data, status, jqXHR) {

			// if we are hiding a busy indicator, we should do so here

			// NOTE: we expect the host page to override the default
			// error messages if they're unsuitable

			//
			// looked like success but there was no identifiable
			// response (type 6--early test)
			//
			if (data.sculpt != 'ajax')
			{
				// missing marker for properly-formatted messages
				this.show_error(this.messages.ajax_garbled, function() {
					if (typeof(failure) == "function")
						failure(false, data, status, null, jqXHR);
				});
			}

			//
			// success-but-failure modes (type 4)
			//

			// case 4a: server redirect
			// the server is asking us to redirect the entire page
			if (data.location != undefined)
			{
				window.location = data.location;
			}

			// case 4b: server exception
			// if we have a backtrace, go ahead and display it,
			// otherwise show the GENERIC error response
			else if (data.exception != undefined)
			{
				// reprocess the resulting error message to include
				// the backtrace, if we have one; otherwise use the
				// canned message
				if (data.exception.backtrace != undefined)
					data.exception.message = '<pre>' + this.escape_html(data.exception.backtrace) + '</pre>';
				else
					data.exception = this.messages.ajax_exception;

				this.show_error(data.exception, function() {
					if (typeof(failure) == "function")
						failure(false, data, status, null, jqXHR);
				}, data.exception.backtrace != undefined ? 'large' : this.default_modal_size);
			}

			// case 4c: form validation errors
			// since this is complex, we'll just hand this off
			else if (data.form_error != undefined)
			{
				this.show_form_error(data.form_error, function() {
					if (data.form_error.length == 0)
					{
						// zero errors means successful validation;
						// this state might be the result of partial
						// validation so it's not wrong
						if (typeof(success) == "function")
							success(true, data, status, null, jqXHR);
					}
					else
					{
						// we have at least one error, so we invoke
						// the failure callback
						if (typeof(failure) == "function")
							failure(false, data, status, null, jqXHR);
					}
				}, data.partial, data.error);
			}

			// case 4d: processing error
			// we show this error directly to the user, as the server
			// intended
			else if (data.error != undefined)
			{
				this.show_error(data.error, function() {
					if (typeof(failure) == "function")
						failure(false, data, status, null, jqXHR);
				});
			}

			//
			// actual success modes (types 5, 6)
			//

			else
			{
				// by default, do NOT invoke the success handler when we're done
				var invoke_success = false;

				// case 5a: request-specific data
				// this is completely app-specific so we invoke the success
				// handler right now without doing anything else
				if (data.results != undefined)
				{
					if (typeof(success) == "function")
						success(true, data, status, null, jqXHR);
					return;	// STOP NOW
				}

				// the remaining cases are not mutually-exclusive

				// case 5b: HTML results
				if (data.html != undefined)
				{
					this.update_html(data.html);
					invoke_success = true;
				}

				// case 5c: toast results
				// server-side accepts a single dict but always
				// gives it to us as a list, even though multiple
				// toasts are NOT recommended (bad UX)
				if (data.toast != undefined)
				{
					for (var i = 0; i < data.toast.length; i++)
						this.queue_toast(data.toast[i]);
					invoke_success = true;
				}

				// case 5d: modal results
				// in this case we don't want to invoke the success
				// handler automatically because it needs to wait
				// until after the modal is closed
				if (data.modal != undefined)
				{
					this.show_modal(data.modal, function() {
						if (typeof(success) == "function")
							success(true, data, status, null, jqXHR);
					});
					return;
				}

				// otherwise invoke the success handler if we have
				// a recognized success response (5b, 5c)
				if (invoke_success)
				{
					if (typeof(success) == "function")
						success(true, data, status, null, jqXHR);
					return;
				}

				//
				// looked like success but there was no identifiable
				// response (type 6)
				//

				this.show_error(this.messages.ajax_garbled, function() {
					if (typeof(failure) == "function")
						failure(false, data, status, null, jqXHR);
				});
			}
		},

		// whenever an AJAX method "fails", this is called
		// NOTE: each case must clean up busy indicators
		'_ajax_failure': function (success, failure, fail_silently, show_busy, jqXHR, status, message) {

			// if we are hiding a busy indicator, we should do so here

			// NOTE: these error texts ultimately should be fetched from the
			// host page, so that they can be customized based on the user's
			// language and the site in question

			// type 1: the request may have timed out
			if (status == "timeout")
			{
				this.show_error(this.messages.ajax_timeout, function() {
					if (typeof(failure) == "function")
						failure(false, null, status, message, jqXHR);
				});
			}

			// types 2, 3: the server returned an actual error status
			// without a body or success with unparseable JSON
			else if (status == "error" || status == "parsererror")
			{
				this.show_error(this.messages.ajax_garbled, function() {
					if (typeof(failure) == "function")
						failure(false, null, status, message, jqXHR);
				});
			}

			// This is for when you are doing thinks like predictive search
			// when you are cancelling requests with abort(), if you want to
			// fail silently you have the option to do so, but understand that
			// it could have unexpected consequences.  Use at your own risk.
			// (Specifically: if the server reports an error message the user
			// needs to see, such as they've been logged out and need to be
			// told to log in again, you are suppressing that display.)
			// QUESTION: shouldn't this actually be handled as the first case?
			// ANSWER: not necessarily. In some cases where the user might
			// have a lot of data entered on a page (e.g. something more app-
			// like) then we would want to do the login inline and/or let
			// them decide what to do rather than summarily dumping the page
			// with a redirect.
			else if (fail_silently)
			{
				if (typeof(failure) == "function")
					failure(false, null, status, message, jqXHR);
			}

			// ...this should happen; the request has been aborted
			// by client-side code (maybe a canceled upload?)
			else
			{
				this.show_error(this.messages.ajax_canceled, function() {
					if (typeof(failure) == "function")
						failure(false, null, status, message, jqXHR);
				});
			}
		},

		// log a console.error then call show_modal
		'show_error': function (error, done, size) {
			console.error('ERROR: <' + error.title + '> ' + error.message);
			this.show_modal(error, done, size);
		},

		// show a simple, canned message to the user
		'show_modal': function (data, done, size) {

			// try to get a default size for the modal
			if (typeof(size) == 'undefined')
			{
				// none given; see if the modal itself
				// specifies a size
				if (typeof(data.size) == 'undefined')
					size = this.default_modal_size;
				else
					size = data.size;
			}

			// alternate version: we're showing a modal supplied by the
			// server, which we expect to contain all the necessary
			// HTML, including the frame
			if (size == 'raw')
			{
				// this totally short-circuits the rest of the logic
				// as this modal is completely self-contained; however,
				// we need to save the original modal template so we
				// can restore it when we're done
				var original_modal = $('#sculpt_modal').children().detach();
				$('#sculpt_modal').empty().append(data.message).modal().on(
					'hidden.bs.modal', function(e){
						// should check that this is the right modal
						$('#sculpt_modal').empty().append(original_modal);
					}
				);

				return;
			}

			// set up the modal
			$('#sculpt_modal .modal-dialog').removeClass('modal-lg modal-md modal-sm');

			if (size == 'large')
				$('#sculpt_modal .modal-dialog').addClass('modal-lg');
			else if (size == 'medium')
				$('#sculpt_modal .modal-dialog').addClass('modal-md');
			else if (size == 'small')
				$('#sculpt_modal .modal-dialog').addClass('modal-sm');
			else	// unrecognized size, assume it's a class name
				$('#sculpt_modal .modal-dialog').addClass(size);

			$('#sculpt_modal_title').html(data.title);
			$('#sculpt_modal_body').html(data.message);

			var button_label = 'Close';
			if (typeof(data.button_label) != 'undefined')
				button_label = data.button_label;

			$('#sculpt_modal_button').html(button_label);

			// set up result processing, so that modals can detect
			// whether they were canceled or continued
			this.last_modal_result = null;
			var that = this;
			$('#sculpt_modal_button').off('click.sculpt.modal_button').on('click.sculpt.modal_button', function(e){
				that.last_modal_result = 1;
			});

			// set up the event handlers
			// NOTE: we attach this with one() instead of on() so
			// that jQuery will automatically remove the event
			// handler after it runs, so the next error message
			// shown will not invoke the old handler
			$('#sculpt_modal').one('hide.bs.modal', function (e) {
				if (typeof(done) == "function")
					done(0);
			});

			// show the modal
			$('#sculpt_modal').modal();
		},

		// process a list of HTML updates (typically, but not necessarily,
		// in response to an AJAX request)
		'update_html': function (update_list) {
			var i;
			var update_item;

			for (i = 0; i < update_list.length; i++)
			{
				update_item = update_list[i];
				var obj = $('#'+update_item.id);
				
				// append, prepend, or replace
				if (update_item.mode == 'append')
					obj.append(update_item.html);
				else if (update_item.mode == 'prepend')
					obj.prepend(update_item.html);
				else if (update_item.mode == 'before')
					obj.before(update_item.html);
				else if (update_item.mode == 'after')
					obj.after(update_item.html);
				else if (update_item.mode == 'replace')
					obj.replaceWith(update_item.html);
				else if (update_item.mode == 'remove')
				{
					obj.remove();
					continue;				// no class updates on removed object
				}
				else if (update_item.mode != 'noop')
					obj.html(update_item.html);

				// add/remove classes, if requested
				// NOTE: you may find replace mode more
				// effective than manipulating classes
				if (update_item.class_add != undefined)
					obj.addClass(update_item.class_add);
				if (update_item.class_remove != undefined)
					obj.removeClass(update_item.class_remove);

				// show/hide, if requested
				if (update_item.display == 'show')
					obj.show();
				else if (update_item.display == 'hide')
					obj.hide();

				this._init_chosen($('#'+update_item.id)[0]);	// set up chosen on any selects in fresh HTML
			}
		},

		//
		// COOKIE ACCESS
		//
		// The browser provides access to cookies via document.cookie, but this
		// is inconvenient when searching for specific cookies. We provide a
		// simple extractor. After invoking extract_cookies(), the collection
		// will be available in Sculpt.cookies.
		//

		'extract_cookies': function () {
			this.cookies = {};
			if (document.cookie && document.cookie != '')
			{
				var cookies = document.cookie.split(';');
				for (var i = 0; i < cookies.length; i++)
				{
					// we'd like to use .split here and just limit it to 2, but
					// JavaScript's split applies the limit after the splits have
					// already been done, rather than Python's split which just
					// stops splitting:
					// '1:2:3'.split(':',2)	==JS==> ['1','2']
					// '1:2:3'.split(':',2)	==Py==> ['1','2:3']
					var cookie_trimmed = $.trim(cookies[i]);
					var split_position = cookie_trimmed.indexOf('=');
					if (split_position >= 0)
					{
						var cookie_name = cookie_trimmed.substr(0, split_position);
						var cookie_value = decodeURIComponent(cookie_trimmed.substr(split_position+1));
						this.cookies[cookie_name] = cookie_value;
					}
				}
			}
		},

		//
		// CONSOLE WRAPPING
		//
		// Because IE. Specifically, Internet Explorer in older versions
		// leaves the console object undefined unless the console window
		// is open. Ouch.
		//

		'_wrap_console': function () {
			if (typeof(window.console) == 'undefined')
			{
				window.console = {
					'log': function () {},
					'error': function () {},
					'info': function () {},
					'debug': function () {}
				};
			}
		},

		//
		// FORM HANDLING
		//

		// A common use case is that we want all the regular AJAX form
		// handling, but we want to attach additional handling for
		// success or failure (i.e. we're expecting data rather than
		// a redirect or form error) and we don't want to keep writing
		// boilerplate submit handlers for this very common pattern.
		// Instead we register automatic handlers, which will be used
		// for automatically-submitted forms.
		//
		// In addition to success and failure handlers, you can create
		// a "prepare" handler which is invoked prior to form
		// processing; if it returns a non-zero value, the form will
		// not be submitted to the server.
		//
		'register_form_handlers': function (f_id, prepare, success, failure, show_busy) {
			this.auto_form_handlers[f_id] = { 'id': f_id, 'prepare': prepare, 'success': success, 'failure': failure, 'show_busy': show_busy };
		},

		// Redirect submission handler of all forms to our wrapper code.
		// Exclude any form with the class "_sculpt_no_ajax" so that we
		// can deal with exceptional cases.
		// NOTE: we delegate this event handler to the document, rather
		// than directly attaching it to the form objects, so that any
		// forms loaded via AJAX will still trigger the handler
		'_wrap_forms': function () {
			var that = this;				// the inline function below runs with a different "this" context, so alias it
			$(document).on('submit', 'form:not(._sculpt_no_ajax)', function(e) {
				// NOTE: Firefox does not have a global "event" scope, so
				// we make sure to pluck it from function parameters
				e.preventDefault();			// do not let the form submit normally; we are doing that here
				that._skip_partial_validation = this.id;	// this form should not be partially-validated due to blur as we're fully-validating it
				if (this.id in that.auto_form_handlers)
				{
					if (typeof(that.auto_form_handlers[this.id].prepare) == "function")
						if (that.auto_form_handlers[this.id].prepare(this))
							return;
					// submit the form via AJAX and handle the results as indicated
					that.ajax_form($(this), that.auto_form_handlers[this.id].success, that.auto_form_handlers[this.id].failure, that.auto_form_handlers[this.id].show_busy);
				}
				else
					that.ajax_form($(this));	// submit the form via AJAX and handle the results internally
			});

			// set up file handling
			$(document).on('change', 'form._sculpt_ajax_upload input[type=file]', function(e) {
				var form = $(this).parents('form._sculpt_ajax_upload')[0];

				if (form.id in that.auto_form_handlers)
				{
					if (typeof(that.auto_form_handlers[form.id].prepare) == "function")
						if (that.auto_form_handlers[form.id].prepare(this))
							return;
					// submit the form via AJAX and handle the results as indicated
					that._upload_new_file(e, this, that.auto_form_handlers[form.id].success, that.auto_form_handlers[form.id].failure, that.auto_form_handlers[form.id].show_busy);
				}
				else
					that._upload_new_file(e, this);
			});

			// set up partial validation
			$(document).on('focusout.sculpt.partial_validation', 'form._sculpt_ajax_partial .form-group select, form._sculpt_ajax_partial .form-group input, form._sculpt_ajax_partial .form-group textarea', function (e) {
				// NOTE: we don't use the registered callbacks for partial
				var form = $(this).parents('form')[0];

				// sometimes we get an event that looks like we should
				// partially validate, but we don't need to because we
				// just submitted the form; check to see if we're meant
				// to ignore the next event on this form
				if (that._skip_partial_validation == form.id)
				{
					that._skip_partial_validation = null;
					return;
				}

				// Fun wrinkle: using chosen to replace SELECT tags with
				// typeable, searchable drop-downs means the visible
				// input control has no name and no ID. This makes it hard
				// to identify the actual select field that we want to
				// say is the focus field.
				//
				// The easy and forward-looking approach is to find the
				// form-control object if the current input does not have
				// a name.
				var ff = this;
				if (ff.name == undefined || ff.name == '')
					ff = $(this).closest('.form-group').find('.form-control')[0];

				// we need to keep track of two fields: the field the user
				// just focused out of (the one that triggered this event)
				// and the "last" field on the form the user actually
				// entered; this is so that we can validate up to and
				// including that last field, even if the user focuses
				// back on an earlier field (e.g. to correct a mistake
				// we've highlighted for them)
				//
				// the "last" field is tricky to extract and, since we
				// extract it in DOM order, may not match the field order
				// stored on the server; since eventually all fields will
				// be validated, we can live with the potential for
				// inconsistency (for now)
				//
				var last_field = $(form).data('lastField');
				if (last_field == undefined)
				{
					// we never recorded one on this form; use the focus
					// field
					$(form).data('lastField', ff);
					last_field = ff;
				}
				else
				{
					// we have one; see if the current focus field is
					// "after" it by comparing their DOM positions
					if ($(last_field).isBefore($(ff)))
					{
						// this new field is farther into the form
						// than the previous last field
						$(form).data('lastField', ff);
						last_field = ff;
					}
				}

				// submit the form via AJAX and handle the results internally
				that.ajax_form($(form), null, null, false, ff.name, last_field.name);
			});
		},

		// actually submit a form; pulled into its own function so that
		// if you programmatically need to submit an existing form, you
		// can and still get the AJAX functionality
		//
		// NOTE: expects to be passed a jQuery-wrapped form object, NOT
		// a bare form
		//
		// NOTE: although you can pass success/failure callbacks to this,
		// and they will be passed into the core AJAX handler, normal
		// form processing will not require them as the normal response
		// is to either present validation errors (handled for you) or
		// to redirect to a new page (handled for you)
		//
		'ajax_form': function (f, success, failure, show_busy, focus_field, last_field) {
			var is_partial = (typeof(last_field) != 'undefined');
			var post_data = f.serialize();
			var action = f[0].action;

			if (is_partial)
				// tell the server this is partial (assumes no other GET params)
				action += '?_partial='+last_field+'&_focus='+focus_field;
			else
				// only clear the fields now if we're fully-submitting
				this.clear_form_errors(f, true);

			this.ajax({
				'url': action,
				'data': post_data
			}, function(succeeded, data, status, message, jqXHR) {
				// partial validation should not process either
				// close or clear classes as the form isn't complete
				if (is_partial)
					return;

				// extra quirk: if the form itself is marked
				// with the _sculpt_ajax_autoclose class, search
				// upwards for a modal object and close it
				if (f.hasClass('_sculpt_ajax_autoclose'))
				{
					var o = f.parents('.modal');
					if (o)
						$(o[0]).modal("hide");
				}

				// similarly, if the form itself is marked
				// with the _sculpt_ajax_autoclear class, reset
				// the form
				if (f.hasClass('_sculpt_ajax_autoclear'))
					f[0].reset();

				// invoke the regular success handler, if
				// one was provided
				if (typeof(success) == "function")
					success(succeeded, data, status, message, jqXHR);
			}, failure, show_busy);
		},

		// clear all the error markers from a form
		'clear_form_errors': function (f, clear_tooltips) {
			// Sculpt class
			// this is attached directly to the field, as is the tooltip
			if (clear_tooltips)
				f.find('.error').removeClass('error').tooltip('destroy');
			else
				f.find('.error').removeClass('error');

			// Bootstrap 3 classes
			// these are attached to the nearest parent form-group
			f.find('.has-success').removeClass('has-success');
			f.find('.has-warning').removeClass('has-warning');
			f.find('.has-error').removeClass('has-error');
		},

		// given a set of form errors, show them to the user
		'show_form_error': function (form_error, done, partial, error_modal) {
			var is_partial = (typeof(partial) != 'undefined');			// whether this is a partial validation result
			var error = $.extend({}, this.messages.ajax_form_error);	// first-level copy so we don't modify the original
			var messages = [];
			var deduplicator = {};
			var i;
			var j;

			// identify the form that we just validated, using
			// either the first errored field (if it was a full
			// validation) or the last_field specified in partial
			// validation
			//
			var f;
			if (is_partial)
				f = $('#id_'+partial.last_field).closest('form');
			else
				f = $('#id_'+form_error[0][0]).closest('form');

			// if this is partial validation, the form errors
			// will not have been cleared yet (to present a
			// nicer user experience by not flashing the error
			// states every time they tab between fields);
			// go ahead and clear them now
			//
			// NOTE: we have to do this before processing the
			// error list because that processing will apply
			// the classes to the form groups
			//
			// NOTE: we also don't clear tooltips here, as we
			// might clobber the one the user is looking at;
			// instead we check that as we process them
			//
			if (is_partial)
				this.clear_form_errors(f, false);

			// assemble the error message list
			// and highlight the form groups that have errors
			for (i = 0; i < form_error.length; i++)
			{
				var field_name = form_error[i][0];
				var field_label = form_error[i][1];
				var field_errors = form_error[i][2];
				var field_messages = [];
				for (j = 0; j < field_errors.length; j++)
				{
					var message = field_errors[j];
					var field_message = message;

					// substitute in the full field name
					if (field_name != null)
					{
						field_message = message.replace(/__fieldname__/g, 'This');	// field-specific version
						message = message.replace(/__fieldname__/g, field_label);	// summary version
					}

					// if, after substitution, this is a new message,
					// go ahead and add it to the list
					if (!(message in deduplicator))
					{
						deduplicator[message] = true;	// update deduplicator so we know when we see it next

						// splice this error into our item formatter string
						messages[messages.length] = this.messages.ajax_form_error_item.replace(/__error_item__/g, message);
					}

					// collect up the error message for per-field display
					field_messages[field_messages.length] = this.messages.ajax_field_error_item.replace(/__error_item__/g, field_message);
				}

				// mark the input with an error class
				var ff = $('#id_'+field_name);
				ff.addClass('error');

				// add tooltips
				// ****TODO: use top for selects
				// extra wrinkle: just blindly setting the tooltip looks
				// ugly if it's currently being displayed and it hasn't
				// changed--it blinks, which is visually distracting.
				// check to see if it's changed before setting it
				var tt_message = this.messages.ajax_field_error.replace(/__error_list__/g, field_messages.join("\n"));
				var tt_data = ff.data('bs.tooltip');	// fetch Bootstrap Tooltip object
				if (tt_data == undefined || tt_data.getTitle() != tt_message)
				{
					ff.tooltip({
						'html': true,
						'placement':  'bottom',
						'title': tt_message,
						'trigger': 'focus'	// default is "hover focus" but hover causes tooltip to disappear on casual mouse movement
					});
				}

				// and mark the control group for Bootstrap 3
				ff.closest('.form-group').addClass('has-error');
			}

			// mark all the non-error, non-warning fields with a
			// success flag; with partial validation, stop at the
			// last field known to be tested
			//
			// NOTE: we have to loop over the whole set with each()
			// because we need to stop as soon as we get to the
			// last validated field, and that field might or might
			// not have an error
			//
			f.find('.form-group').each(function (i) {
				var fg = $(this);
				if (!fg.hasClass('has-error') && !fg.hasClass('has-warning'))
				{
					fg.addClass('has-success');
					// if the user is focused in this field it's
					// possible we didn't destroy an old error
					// tooltip
					var fc = fg.find('.form-control');
					fc.tooltip('destroy');
				}
				if (is_partial && $(this).find('[name='+partial.last_field+']').length > 0)	// stop if we find our last field in this form-group
					return false;
			});

			// it's possible the user is currently focused on a
			// field, and when we cleared the form of errors and
			// set up new ones, we clobbered the tooltip they
			// were looking at; find any focused field that has
			// errors and show its tooltip, just to be sure
			//f.find('.error:focus').tooltip('show');

			// for full validation, summarize the errors for the
			// user in a modal
			if (!is_partial)
			{
				if (error_modal != undefined)
				{
					// the server has provided a complete
					// summary of the errors itself (normally
					// because there is one error, and it
					// requires a more detailed explanation
					// than is appropriate for field popup text)
					this.show_error(error_modal, done);
				}
				else
				{
					// no summary error message was given, use
					// our generated one
					error.message = error.message.replace(/__error_list__/g, messages.join("\n"));
					this.show_error(error, done, this.default_formerror_modal_size);
				}
			}
		},

		//
		// FILE UPLOAD
		//

		// when file input object receives new files
		'_upload_new_file': function(e, ff, success, failure, show_busy) {
			var that = this;

			// pluck out File object from updated input object
			var file_list = ff.files;
			//for (var i = 0; i < file_list.length; i++)
			//	console.log(i, file_list[i].name, file_list[i].size, file_list[i].type);
			var parent_form = $(ff).closest('form');

			// create a customized XHR that includes progress
			var form_data = new FormData(parent_form[0]);
			var jqXHR = this.ajax({
				// the actual data
				data: form_data,
				contentType: false,
				processData: false,

				url: parent_form[0].action,

				// custom XHR
				xhr: function() {
					var custom_xhr = $.ajaxSettings.xhr();
					if (custom_xhr.upload)
						custom_xhr.upload.addEventListener('progress', function (e) {
							return that._upload_progress(e, that);
						}, false);
					return custom_xhr;
				}
			}, this._upload_success(success), this._upload_failure(failure), show_busy, false);

			// hide the input field (we are hard-coding for 1 file right now)
			// and show the list
			$('#div_id_uploaded_file').hide();
			$('#sculpt_uploaded_file_list').show();

			// build an item to go in the list
			this.upload_queue = [{ name: file_list[0].name, size: file_list[0].size, form: parent_form }];
			var message = this._upload_progress_format(file_list[0].name, 0.0);
			$('#uploaded_file_list ul').html(message);
		},

		// process the upload queue
		'_upload_queued_file': function () {
		},

		// when an upload has a progress event
		// NOTE: "this" refers to the XHRupload object
		'_upload_progress': function (e, that) {
			if (e.lengthComputable)
			{
				var percentage = Math.round((e.loaded * 100.0) / e.total);
				var message = that._upload_progress_format(that.upload_queue[0].name, percentage);
				$('#uploaded_file_list ul').html(message);
			}
		},

		// when an upload succeeds
		'_upload_success': function(success_fn){
			var inner = function (success, data, status, message, jqXHR) {
				// NOTE: "this" refers to window, and the function signature
				// is set by Sculpt.ajax, so we resort to an explicit reference
				// to Sculpt. *sigh*
				var that = Sculpt;

				// update the progress message to show 100%
				var message = that._upload_progress_format(that.upload_queue[0].name, 100.0);
				$('#uploaded_file_list ul').html(message);

				// write the file ID into the hidden field
				var target_form_id = that.upload_queue[0].form.attr('data-target-form-id');
				var target_field_id = that.upload_queue[0].form.attr('data-target-field-id');
				$('#'+target_field_id)[0].value = data.results.file.hash;

				if (typeof(success_fn) == "function")
					success_fn(success, data, status, message, jqXHR);
			};
			return inner;
		},

		// when an upload fails
		'_upload_failure': function (failure_fn) {
			var inner = function (success, data, status, message, jqXHR) {
				console.error('upload failure');
				if (typeof(failure_fn) == "function")
					failure_fn(success, data, status, message, jqXHR)
			};
			return inner;
		},

		// formatting a progress message
		'_upload_progress_format': function (filename, percentage) {
			if (percentage < 100.0)
			{
				percentage = Math.round(percentage * 10.0) * 0.1;
				return this.messages.ajax_upload_item_incomplete.replace(/__item_filename__/g, filename).replace(/__item_progress_percent__/g, percentage.toString());
			}
			else
				return this.messages.ajax_upload_item_complete.replace(/__item_filename__/g, filename);
		},

		//
		// TOAST
		//

		// adapted from Blake Compton's toast.js

		'toast_defaults': {
			'duration': 0,								// default is for toast to never automatically disappear, requiring manual dismissal
			'delay': 500,								// how long to wait between consecutive toasts; if 0, no delay (and thus no time for animations!)
			'class_name': 'toast-success',				// CSS class used for toast, if any
			'delivered': null,							// default callback for when toast is delivered (shown)
			'dismissed': null,							// default callback for when toast is dismissed (via timer or user dismissal)
			'removed': null								// default callback for when toast is removed (programmatically; rarely used)
		},
		'_toast_cache': null,
		'_toast_queue': [],
		'_toast_element': null,							// HTML element that actually is the toast
		'_toast_next_id': 16777216,						// 0x1000000

		// add a toast to the toast queue
		// NOTE: this is how toast should ALWAYS be created;
		// it ensures new toast will not clobber existing
		// toast
		//
		// overridable options:
		//	html		actual HTML to display
		//	duration	how long, in milliseconds, to show the toast before auto-dismissing it; 0 means manual dismissal is required
		//	delivered	callback for when toast is shown
		//	dismissed	callback for when toast is dismissed (via timer or user click)
		//	removed		callback for when toast is removed (via code)
		//
		'queue_toast': function (options) {
			// we need a unique name
			this._toast_next_id++;
			var unique_name = 'toast_' + this._toast_next_id.toString(16);	// not random, thus guaranteed to be unique until integer overflow (about 2 billion toast per page refresh)

			// merge the options we have with our default options
			var toast = $.extend({
				// these options can be overridden
				'html': 'Success'						// this one should ALWAYS be overridden
			}, this.toast_defaults, options, {
				// these options can't be overridden
				'id': unique_name,						// IDs are always generated internally
				'timer': null							// timer is filled in when toast is displayed
			});

			// queue it up; if this is the only item in the
			// queue, process the queue now (to show the
			// toast)
			this._toast_queue.push(toast);
			if (this._toast_queue.length == 1)
				this._process_toast_queue();

			return toast.id;
		},

		// process the queue and, if necessary, create an
		// actual, visible toast
		'_process_toast_queue': function () {
			// if we have a visible toast already, do nothing;
			// the toast needs to be dismissed first
			if (this._toast_element.hasClass('active'))
				return;

			// if the queue isn't empty, deliver more toast
			if (this._toast_queue.length > 0)
				this._deliver_toast();
		},

		// actually show a user toast
		'_deliver_toast': function () {
			var toast = this._toast_queue[0];

			// change the toast to the new content and show it
			// NOTE: animations performed via CSS
			// NOTE: we strip ALL classes before adding, because
			// we need to leave the subclass on an expiring toast
			// long enough for the transition to occur, but by the
			// time we deliver the next toast we don't know what
			// class to remove. So we make a rule, no subclasses
			// will be used except the ones specified in toast
			// queueing.
			this._toast_element.html(toast.html).removeClass().addClass('active');
			if (toast.class_name != null)
				this._toast_element.addClass(toast.class_name);

			// set up timer
			// NOTE: we do this first in the rare chance that the
			// callback takes a long time; the timer should start
			// as soon as the toast is visible, and if your callback
			// is slow, use a longer timeout
			if (toast.duration > 0)
			{
				var that = this;
				toast.timer = window.setTimeout(function(){
					toast.timer = null;		// no need to clear this timeout as it's already occurred
					that.dismiss_toast();	// hide the toast and process the next one
				}, toast.duration);
			}

			// trigger callback
			if (toast.delivered != null)
				toast.delivered(toast);
		},

		// dismiss current toast (does not require ID)
		'dismiss_toast': function () {
			var toast = this._toast_queue[0];

			// hide the current toast, but leave the subclass
			// on it so animations will work
			this._toast_element.removeClass('active').addClass('inactive');

			// if there is still a timeout waiting, kill it
			if (toast.timer)
				window.clearTimeout(toast.timer);

			// trigger callback
			if (toast.dismissed != null)
				toast.dismissed(toast);

			// bump this from the queue
			this._toast_queue.splice(0,1);

			// and process the queue
			if (toast.delay == 0)
				this._process_toast_queue();		// process queue now
			else
			{
				var that = this;
				window.setTimeout(function(){		// process queue after a short delay
					that._process_toast_queue();
				}, toast.delay);
			}
		},

		// remove a toast, whether visible or not
		'remove_toast': function (id) {
			// find the toast INDEX
			// this is important because if it turns out the toast is
			// in slot 0, it's the currently-active toast
			var i = 0;
			for ( ; i < this._toast_queue.length; i++)
				if (this._toast_queue[i].id == id)
					break;
			if (i >= this._toast_queue.length)		// toast ID not found; do nothing
				return;

			// trigger callback
			if (toast.removed != null)
				toast.removed(toast);

			// remove it from the queue
			// done differently depending on whether it's active or not
			if (i == 0)
			{
				// currently-active toast is a bit of a problem; we need
				// to make sure the dismissed callback isn't fired
				toast.dismissed = null;
				this.dismiss_toast();
			}

			else
			{
				// this is an as-yet undelivered toast; we just drop it
				// from the queue as though it never existed
				this._toast_queue.splice(i,1);
			}
		},

		// set up the toast system
		'_init_toast': function () {
			if (this._toast_element == null)
				this._toast_element = $('#toast');		// by default; app may override
			var that = this;
			this._toast_element.on('click', function (e) {
				that.dismiss_toast();					// dismiss toast when clicked
			});
		},

		//
		// LIVE UPDATE FIELDS
		//
		// Live update fields allow us to POST the contents of a field back
		// to the server as it is being edited.
		//

		'live_update_focused_field': null,
		'live_update_was_changed': false,
		'live_update_key_timer': null,
		'live_update_default_delay': 250,	// quarter-second response rate

		'_init_live_update': function () {
			var that = this;
			$(document).on('focusin.sculpt.liveupdate', '._sculpt_ajax_live', function (e) {
				// see if we have an existing field we're tracking
				// (in case we see the focus on the new field before
				// the blur on the old field, which happens in some
				// old browsers)
				if (that.live_update_focused_field != null)
					that._live_update_blur();

				// set up the new field
				that.live_update_focused_field = this;

			}).on('keydown.sculpt.liveupdate', '._sculpt_ajax_live', function (e) {
				// we need to use keydown events because change doesn't
				// fire until the user tabs out of the field

				// mark this field as changed
				that.live_update_was_changed = true;

				// for change events, we don't submit right away, but
				// we wait for some period
				var delay = parseInt($(this).attr('data-live-update-delay'), 10);	// make sure we parse as base 10, thank you

				// apply default if the field doesn't set a delay
				if (isNaN(delay))
					delay = that.live_update_default_delay;

				// only set up the timer if we have a delay
				if (delay != 0)
					that.live_update_key_timer = window.setTimeout(function () {
						that._live_update_submit();		// we know it's changed, submit it
					}, delay);

			}).on('focusout.sculpt.liveupdate', '._sculpt_ajax_live', function (e) {
				that._live_update_blur();

			}).on('change.sculpt.liveupdate', 'select._sculpt_ajax_live', function (e) {
				that._live_update_submit();

			});
		},

		'_live_update_blur': function () {
			if (this.live_update_focused_field != null)
			{
				// only bother to submit if the field was actually changed
				if (this.live_update_was_changed)
					this._live_update_submit();

				// make sure we indicate we're no longer tracking any field
				this.live_update_focused_field = null;
			}
		},

		'_live_update_submit': function () {
			var jq_field = $(this.live_update_focused_field);

			// clobber the timer if it's still pending
			if (this.live_update_key_timer != null)
			{
				window.clearTimeout(this.live_update_key_timer);
				this.live_update_key_timer = null;
			}

			// zap the changed flag; we don't care any more
			this.live_update_was_changed = false;

			// post the data to the server (automatic responses expected)
			this.ajax({
				url: jq_field.attr('data-live-update-action'),
				data: jq_field.serialize()		// just this one field, please
			});
		},


		//
		// UTILITIES
		//
		'escape_html': function (s) {
			return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
		},

		// any link with an _ajax_post class should treat its HREF as
		// a place to make an empty POST to via AJAX; handlers can be
		// attached in the same way as forms (via register_form_handlers)
		// we also wrap _decorative links and swallow their clicks
		'_wrap_links': function () {
			var that = this;

			$(document).on('click', 'a._sculpt_ajax_post', function (e) {
				var other = this;
				e.preventDefault();

				// we may be working on a link inside a modal,
				// which needs to close the modal before making
				// a request that might trigger another modal
				if ($(other).hasClass('_sculpt_modal_dismiss'))
					$('#sculpt_modal').modal('hide');

				// check for prepare handler
				if (other.id in that.auto_form_handlers)
					if (typeof(that.auto_form_handlers[other.id].prepare) == 'function')
						if (that.auto_form_handlers[other.id].prepare(other))
							return;

				// determine parameters for AJAX call; mostly nothing,
				// unless form handlers were registered
				var success = null;
				var failure = null;
				var show_busy = false;

				if (other.id in that.auto_form_handlers)
				{
					success = that.auto_form_handlers[other.id].success;
					failure = that.auto_form_handlers[other.id].failure;
					show_busy = that.auto_form_handlers[other.id].show_busy;
				}

				// make the AJAX call, with handlers
				that.ajax({
					'url': this.href,
					'data': { 'csrfmiddlewaretoken': that.cookies.csrftoken }
				}, success, failure, show_busy, false);
			});

			$(document).on('click', 'a._sculpt_decorative', function (e) {
				e.preventDefault();
			});
		},

		'_init_chosen': function (dom_node) {
			$(this.chosen_selector).chosen({ disable_search_threshold: 20 }, dom_node);
		},

		//
		// TEMPLATES
		//
		// Some things need to be rendered directly by the library without
		// making additional AJAX calls.
		//

		// error messages
		'messages': {
			'ajax_timeout':			{ 'title': 'Timeout',				'message': '<p>The server did not respond quickly enough. It may be temporarily unavailable, or your connection to the internet may have been interrupted.</p>' },
			'ajax_canceled':		{ 'title': 'Cancelled',				'message': '<p>You canceled the operation.</p>' },
			'ajax_garbled':			{ 'title': 'Garbled Response',		'message': '<p>The server responded in an unexpected way. It&#8217;s possible the server is having problems or your internet connection may have been interrupted.</p>' },
			'ajax_exception':		{ 'title': 'Server Error',			'message': '<p>The server responded with an error. We&#8217;ve notified our development team and they&#8217;ll take a look at the problem.</p>' },
			'ajax_form_error':		{ 'title': 'Corrections Required',	'message': '<p>There are problems with the data you entered:</p><ul>__error_list__</ul><p>Please make corrections and try again.</p>' },
			'ajax_form_error_item':			'<li>__error_item__</li>',
			'ajax_field_error':				'<ul>__error_list__</ul>',
			'ajax_field_error_item':		'<li>__error_item__</li>',
			'ajax_upload_item_incomplete':	'<li>Uploading __item_filename__ <span class="upload_progress">__item_progress_percent__%</span></li>',
			'ajax_upload_item_complete':	'<li>Uploaded __item_filename__</li>'
		},

		//
		// INITIALIZATION
		//
		// Just invoke this once.
		//
		'init': function () {
			this.extract_cookies();
			this._wrap_console();
			this._wrap_forms();
			this._wrap_links();
			this._init_toast();
			//this._init_chosen(document);
			this._init_live_update();
		}

	};
}(jQuery));

// tiny extension to jQuery to conveniently test
// whether one object occurs before another in
// document order; see
// http://stackoverflow.com/questions/3860351/relative-position-in-dom-of-elements-in-jquery
(function($) {
	$.fn.isBefore = function(elem) {
		if (typeof(elem) == "string")
			// we were given a selector instead of a jQuery object; select elements
			elem = $(elem);

		// add the compared elements to the current selected set;
		// jQuery will automatically insert the new elements BEFORE
		// the existing one(s) in order to maintain DOM order
		//
		/// this lets us look up the index in the list of what
		// we just added, and if it wasn't at the top of the
		// list, the item we had already at the top of the list
		// "is before" what we compared to
		return this.add(elem).index(elem) > 0;
	}
})(jQuery);
