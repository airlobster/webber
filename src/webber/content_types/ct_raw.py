
from collections.abc import Iterable


def raw_tokenizer(content:str) -> Iterable[str]:
	yield content

def raw_renderer(tokens:Iterable[str], links:Iterable[str]=None) -> Iterable[str]:
	yield from tokens
