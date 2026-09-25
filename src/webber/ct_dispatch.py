from collections import namedtuple
from typing import Tuple
from urllib.parse import urlparse, unquote
from pathlib import Path
from fnmatch import fnmatchcase
from webber.content_types.ct_html import html_lexer, html_render
from webber.content_types.ct_raw import raw_tokenizer, raw_renderer
from webber.content_types.ct_json import json_lexer_wrapper, json_renderer_wrapper
from webber.utils import find

ContentTypeHandlers = namedtuple("ContentTypeHandlers", [
		"schema_patterns", "content_type_patterns", "url_extractor", "tokenizer", "renderer"
	]
)

content_type_handlers = [
	# HTML
	ContentTypeHandlers(
		schema_patterns = [ "http?", "file" ],
		content_type_patterns = [ "*/html" ],
		url_extractor = lambda url: url,
		tokenizer = html_lexer,
		renderer = html_render
	),
	# JSON
	ContentTypeHandlers(
		schema_patterns = [ "http?", "file" ],
		content_type_patterns = [ "application/json" ],
		url_extractor = lambda url: url,
		tokenizer = lambda content: json_lexer_wrapper(content),
		renderer = lambda tokens, links: json_renderer_wrapper(tokens)
	),
	# PAGE SOURCE
	ContentTypeHandlers(
		schema_patterns = [ "view-source" ],
		content_type_patterns = [ "*" ],
		url_extractor = lambda url: unquote(url[len("view-source://"):]),
		tokenizer = raw_tokenizer,
		renderer = lambda tokens, links: raw_renderer(tokens)
	),
	# FALLBACK
	ContentTypeHandlers(
		schema_patterns = [ "*" ],
		content_type_patterns = [ "text/plain" ],
		url_extractor = lambda url: url,
		tokenizer = lambda content: content.splitlines(keepends=True),
		renderer = lambda tokens, links: tokens
	),
]

extensions = {
	".html": "text/html",
	".json": "application/json",
	"*": "text/plain"
}

# Get the appropriate content handler based on the URL scheme and content type
def get_content_handler(url:str, content_type:str) -> Tuple|None:
	scheme = urlparse(url).scheme
	if not content_type:
		extension = Path(urlparse(url).path).suffix
		content_type = next((v for k, v in extensions.items() if fnmatchcase(extension, k)), "")
		if not content_type:
			raise ValueError(f"Cannot determine content type for URL: {url}")
	h = find(
		content_type_handlers,
		lambda e: \
			any(fnmatchcase(content_type, p) for p in e.content_type_patterns) \
			and any(fnmatchcase(scheme, p) for p in e.schema_patterns)
		)
	if h:
		return (h.tokenizer, h.renderer)
	raise ValueError(f"Unsupported content type: {content_type}")

# Extract the appropriate URL based on the URL scheme
def extract_url(url:str) -> str:
	scheme = urlparse(url).scheme
	h = find(
		content_type_handlers,
		lambda e: any(fnmatchcase(scheme, p) for p in e.schema_patterns)
	)
	if h:
		return h.url_extractor(url)
	return url
