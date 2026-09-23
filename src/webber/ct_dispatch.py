from collections import namedtuple
from typing import Tuple
from fnmatch import fnmatch
from urllib.parse import urlparse, unquote
from webber.content_types.ct_html import html_lexer, html_render
from webber.content_types.ct_raw import raw_tokenizer, raw_renderer

ContentTypeHandlers = namedtuple("ContentTypeHandlers", [
		"schema_pattern", "content_type_pattern", "url_extractor", "tokenizer", "renderer"
	]
)

content_type_handlers = [
	ContentTypeHandlers(
		schema_pattern = r"https?",
		content_type_pattern = r"*/html",
		url_extractor = lambda url: url,
		tokenizer = html_lexer,
		renderer = html_render
	),
	ContentTypeHandlers(
		schema_pattern = r"source",
		content_type_pattern = r"*",
		url_extractor = lambda url: unquote(url[len("source://"):]),
		tokenizer = raw_tokenizer,
		renderer = raw_renderer
	),
]


def get_content_handler(url:str, content_type:str) -> Tuple|None:
	scheme = urlparse(url).scheme
	h = next((
		h for h in content_type_handlers
		if fnmatch(content_type, h.content_type_pattern) and fnmatch(scheme, h.schema_pattern)
		),
		content_type_handlers[0]
	)
	if not h:
		raise ValueError(f"Unsupported content type: {content_type}")
	return (h.tokenizer, h.renderer)


def extract_url(url:str) -> str:
	scheme = urlparse(url).scheme
	h = next((
		h for h in content_type_handlers
		if fnmatch(scheme, h.schema_pattern)
		),
		content_type_handlers[0]
	)
	return h.url_extractor(url)
