from collections import namedtuple
from typing import Tuple
from urllib.parse import urlparse, unquote
from fnmatch import fnmatchcase
from webber.content_types.ct_html import html_lexer, html_render
from webber.content_types.ct_raw import raw_tokenizer, raw_renderer
from webber.content_types.ct_json import json_lexer, json_parser, json_render

ContentTypeHandlers = namedtuple("ContentTypeHandlers", [
		"schema_pattern", "content_type_pattern", "url_extractor", "tokenizer", "renderer"
	]
)

content_type_handlers = [
	# HTML
	ContentTypeHandlers(
		schema_pattern = "http?",
		content_type_pattern = "*/html",
		url_extractor = lambda url: url,
		tokenizer = html_lexer,
		renderer = html_render
	),
	# JSON
	ContentTypeHandlers(
		schema_pattern = "http?",
		content_type_pattern = "application/json",
		url_extractor = lambda url: url,
		tokenizer = lambda content: json_lexer()(content),
		renderer = lambda tokens, links: json_render(json_parser(tokens), indent=4)
	),
	# PAGE SOURCE
	ContentTypeHandlers(
		schema_pattern = "source",
		content_type_pattern = "*",
		url_extractor = lambda url: unquote(url[len("source://"):]),
		tokenizer = raw_tokenizer,
		renderer = raw_renderer
	),
]

# Get the appropriate content handler based on the URL scheme and content type
def get_content_handler(url:str, content_type:str) -> Tuple|None:
	scheme = urlparse(url).scheme
	for h in content_type_handlers:
		content_type_matches = fnmatchcase(content_type, h.content_type_pattern)
		scheme_matches = fnmatchcase(scheme, h.schema_pattern)
		if content_type_matches and scheme_matches:
			return (h.tokenizer, h.renderer)
	raise ValueError(f"Unsupported content type: {content_type}")


def extract_url(url:str) -> str:
	scheme = urlparse(url).scheme
	h = next((
		h for h in content_type_handlers
		if fnmatchcase(scheme, h.schema_pattern)
		),
		content_type_handlers[0]
	)
	return h.url_extractor(url)
