import os
from contextlib import contextmanager
from pathlib import Path
import jinja2
from webber.context import context


@contextmanager
@context
def generated_page(template_name:str, namespace:dict={}):
	try:
		appname = generated_page.__context__.appname
		rootdir = Path(__file__).parent.resolve()
		templatepath = os.path.join(rootdir, 'templates', template_name+'.jinja2')
		tmphtml = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"{appname}-{template_name}.html")
		with open(templatepath, "r") as f:
			variables = {**namespace, **vars(generated_page.__context__)}
			content = jinja2.Template(f.read()).render(**variables)
			with open(tmphtml, "w") as f_out:
				f_out.write(content)
		yield f"file://{tmphtml}"
	finally:
		pass


@context
def text_from_template(template_name:str, namespace:dict={}):
	rootdir = Path(__file__).parent.resolve()
	templatepath = os.path.join(rootdir, 'templates', template_name+'.jinja2')
	with open(templatepath, "r") as f:
		variables = {**namespace, **vars(text_from_template.__context__)}
		content = jinja2.Template(f.read()).render(**variables)
	return content
