from collections import namedtuple
from fnmatch import fnmatch
from webber.content_types.ct_html import html_lexer, html_render

ContentTypeHandlers = namedtuple("ContentTypeHandlers", ["pattern", "tokenizer", "renderer"])

content_type_handlers = [
	ContentTypeHandlers(
		pattern = r"*/html",
		tokenizer = html_lexer,
		renderer = html_render
	),
]

def get_content_type_handler(content_type:str) -> ContentTypeHandlers|None:
	default_handler = content_type_handlers[0]
	h = next((h for h in content_type_handlers if fnmatch(content_type, h.pattern)), default_handler)
	if not h:
		raise ValueError(f"Unsupported content type: {content_type}")
	return (h.tokenizer, h.renderer)
