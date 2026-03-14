import re
import string

from rapidfuzz import fuzz

_ARTICLES = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
_PUNCT = str.maketrans("", "", string.punctuation)


def normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = _ARTICLES.sub("", title)
    title = title.translate(_PUNCT)
    return " ".join(title.split())


def normalize_author(author: str) -> str:
    author = author.lower().strip()
    author = author.translate(_PUNCT)
    return " ".join(author.split())


def fuzzy_match(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(a, b)
