
from collections.abc import Iterable


def raw_tokenizer(content:str) -> Iterable[str]:
	yield content

def raw_renderer(tokens:Iterable[str]) -> Iterable[str]:
	yield from tokens
