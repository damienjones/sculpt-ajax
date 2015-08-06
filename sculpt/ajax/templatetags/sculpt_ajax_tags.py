from django import template
from django.utils.html import escapejs
from django.utils.safestring import mark_safe

register = template.Library()

class EscapeJSNode(template.Node):

	def __init__(self, nodelist):
		self.nodelist = nodelist

	def render(self, context):
		output = self.nodelist.render(context)
		return escapejs(output)

def escapejs_parser(parser, token):
	nodelist = parser.parse(('endescapejs'))
	parser.delete_first_token()
	return EscapeJSNode(nodelist)
