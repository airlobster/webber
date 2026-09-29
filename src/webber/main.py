import sys
sys.path.append("src")
from typing import Iterable, List
from pathlib import Path
import argparse
import webber.log as log
from webber.config import configurable, reinit_config
from webber.context import set_context, get_context
from webber.ct_dispatch import get_content_handler, extract_url
from webber.utils import (
	intercept,
	handle_broken_pipe,
	restart,
)
from webber.unparsable_argparse import UnparsableArgumentParser
from webber.ansi import ANSI
from webber.tui import tui_session
from webber.algorithms.textmanip import (
	reduce_empty_lines,
	ansi_filter,
	split_lines,
	strip_wrapping_whitespaces,
	fixup_for_bash,
	expand_tabs,
	compress_ansi
)
from webber.tui_lib.prompt_history import WebberTuiHistory
from webber.profile import get_prof_table, print_prof_table, profiled
from webber.themes import load_theme

appname = "webber"
version = "0.2.0"

@profiled
def download_content(url:str):
	from urllib.parse import urlsplit
	from curl_cffi import requests
	surl = urlsplit(url)
	if not surl.scheme:
		url = "https://" + url
	http_conf = vars(get_context().config.http)
	return requests.get(url, headers=dict(http_conf), impersonate="chrome")

@profiled
def navigate(url:str, links:List[str]=None) -> Iterable[str]:
	r = download_content(extract_url(url))
	content_type = r.headers.get('Content-Type', '').split(';')[0]
	encoding = r.encoding if r.encoding else 'utf-8'
	tokenizer, renderer = get_content_handler(url, content_type)
	tokens = intercept(tokenizer(r.content.decode(encoding)), log.debug)
	return renderer(tokens, links)

@profiled
def render_formatted_text(tokens:Iterable, use_colors:bool) -> Iterable[str]:
	stream = \
		compress_ansi(
			ansi_filter(
				fixup_for_bash(
					reduce_empty_lines(
						strip_wrapping_whitespaces(
							split_lines(
								expand_tabs(
									tokens,
									tabsize=4
								),
								keepends=True
							),
						),
						max_empty=2,
					),
				),
				passthrough=use_colors
			)
		)

	for chunk in ''.join(stream).splitlines(keepends=True):
		yield chunk
	yield "\n"


@handle_broken_pipe
def events_loop():
	args = get_context().args
	use_colors = args.colors == "always" or (args.colors == "auto" and sys.stdout.isatty())
	tui_session(
		navigate=navigate,
		render=lambda tokens: render_formatted_text(tokens, use_colors)
	)


@handle_broken_pipe
@profiled
def batch_mode():
	args = get_context().args
	url = get_context().args.url
	use_colors = args.colors == "always" or (args.colors == "auto" and sys.stdout.isatty())
	chunks = render_formatted_text(navigate(url, links=None), use_colors)
	for chunk in chunks:
		print(chunk, sep='', end='')


def parseCommandLine():
	class action_reset(argparse.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			WebberTuiHistory.delete_file()
			reinit_config(appname)
			restart(parser.unparse(namespace, exclude=["reset"]))
			sys.exit(0)
	debug_features = Path.joinpath(Path(sys.argv[0]).parent, "__debug__.py").exists()
	parser = UnparsableArgumentParser(description=f"{appname} - command-line web reader", exit_on_error=False)
	parser.add_argument("-v", "--version", action="version", version=f"{appname} {version}")
	parser.add_argument("-b", "--batch", action="store_true", default=False, help="Enable batch mode")
	parser.add_argument("-C", "--colors", choices=["auto", "always", "never"], default="auto", help="Color output mode")
	parser.add_argument("-l", "--log", choices=log.levels, help="Set the logging level", default="INFO")
	parser.add_argument("-N", "--line_numbers", action="store_true", default=False, help="Enable line numbers")
	parser.add_argument("-r", "--reset", nargs=0, action=action_reset, help="Reset the application's history and configuration")
	parser.add_argument("url", nargs="?", help="URL")
	if debug_features:
		parser.add_argument("-d", "--debug", action="store_true", default=False, help="Enable debug mode")
		parser.add_argument("-p", "--profile", action="store_true", default=False, help="Enable profiling")
	return parser.parse_args()


@configurable
def main():
	set_context(appname=appname)

	args = None
	log.set_level("INFO")
	try:
		args = parseCommandLine()
		set_context(args=args)
		log.set_level(args.log)
		if getattr(args, "debug", False):
			# override log level to DEBUG if debug mode is enabled
			log.set_level("TRACE")
		log.trace('CLI args:', args)

		# build application context
		set_context(
			version=version,
			author="Adi Degani",
			email="adid172@gmail.com",
			config=main.__config__,
			palette=load_theme(main.__config__.theme)
		)

		# load last build timestamp
		try:
			with open('TIMESTAMP', 'r') as f:
				set_context(timestamp=f.read().strip())
		except Exception as e:
			pass

		# make sure STDIN is a TTY
		if not sys.stdin.isatty():
			raise RuntimeError("Standard input must be a TTY")

		if not args.url:
			raise RuntimeError("No URL provided")

		# determine if batch mode should be used
		batch_run = args.batch or not sys.stdout.isatty() or not sys.stdin.isatty()
		if batch_run:
			batch_mode()
			return
		events_loop()
	except Exception as e:
		# raise
		if args and getattr(args, "debug", False):
			raise e
		print(f"{log.COLOR_CAT.ERROR}{e}{ANSI.RESET}", file=sys.stderr)
		return 1
	finally:
		if args and getattr(args, "profile", False):
			print_prof_table(get_prof_table())
	return 0


if __name__ == "__main__":
	sys.exit(main())
