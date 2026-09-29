import os
from contextlib import contextmanager
from pathlib import Path
import jinja2
from webber.context import get_context


@contextmanager
def generated_page(template_name:str, namespace:dict={}):
	try:
		appname = get_context("appname")
		rootdir = Path(__file__).parent.resolve()
		templatepath = os.path.join(rootdir, 'templates', template_name+'.jinja2')
		tmphtml = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"{appname}-{template_name}.html")
		with open(templatepath, "r") as f:
			variables = {**namespace, **vars(get_context())}
			content = jinja2.Template(f.read()).render(**variables)
			with open(tmphtml, "w") as f_out:
				f_out.write(content)
		yield f"file://{tmphtml}"
	finally:
		pass


def text_from_template(template_name:str, namespace:dict={}):
	rootdir = Path(__file__).parent.resolve()
	templatepath = os.path.join(rootdir, 'templates', template_name+'.jinja2')
	with open(templatepath, "r") as f:
		variables = {**namespace, **vars(get_context())}
		content = jinja2.Template(f.read()).render(**variables)
	return content
