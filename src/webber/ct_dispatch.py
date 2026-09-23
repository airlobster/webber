from collections import namedtuple
from typing import Tuple
import re
from urllib.parse import urlparse, unquote
from webber.content_types.ct_html import html_lexer, html_render
from webber.content_types.ct_raw import raw_tokenizer, raw_renderer
from webber.content_types.ct_json import json_lexer_wrapper, json_renderer_wrapper

ContentTypeHandlers = namedtuple("ContentTypeHandlers", [
		"schema_pattern", "content_type_pattern", "url_extractor", "tokenizer", "renderer"
	]
)

content_type_handlers = [
	# HTML
	ContentTypeHandlers(
		schema_pattern = re.compile(r"^https?"),
		content_type_pattern = re.compile(r".*/html$"),
		url_extractor = lambda url: url,
		tokenizer = html_lexer,
		renderer = html_render
	),
	# JSON
	ContentTypeHandlers(
		schema_pattern = re.compile(r"^https?"),
		content_type_pattern = re.compile(r"application/json"),
		url_extractor = lambda url: url,
		tokenizer = json_lexer_wrapper,
		renderer = json_renderer_wrapper
	),
	# PAGE SOURCE
	ContentTypeHandlers(
		schema_pattern = re.compile(r"source"),
		content_type_pattern = re.compile(r".+"),
		url_extractor = lambda url: unquote(url[len("source://"):]),
		tokenizer = raw_tokenizer,
		renderer = raw_renderer
	),
]


def get_content_handler(url:str, content_type:str) -> Tuple|None:
	scheme = urlparse(url).scheme
	for h in content_type_handlers:
		content_type_matches = bool(h.content_type_pattern.match(content_type))
		scheme_matches = bool(h.schema_pattern.match(scheme))
		if content_type_matches and scheme_matches:
			return (h.tokenizer, h.renderer)
	raise ValueError(f"Unsupported content type: {content_type}")


def extract_url(url:str) -> str:
	scheme = urlparse(url).scheme
	h = next((
		h for h in content_type_handlers
		if bool(h.schema_pattern.match(scheme))
		),
		content_type_handlers[0]
	)
	return h.url_extractor(url)
