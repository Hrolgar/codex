import isbnlib


def is_valid_isbn(value: str) -> bool:
    clean = value.replace("-", "").replace(" ", "")
    return isbnlib.is_isbn10(clean) or isbnlib.is_isbn13(clean)


def to_isbn13(value: str) -> str | None:
    clean = value.replace("-", "").replace(" ", "")
    if isbnlib.is_isbn13(clean):
        return clean
    if isbnlib.is_isbn10(clean):
        return isbnlib.to_isbn13(clean)
    return None


def to_isbn10(value: str) -> str | None:
    clean = value.replace("-", "").replace(" ", "")
    if isbnlib.is_isbn10(clean):
        return clean
    if isbnlib.is_isbn13(clean):
        return isbnlib.to_isbn10(clean)
    return None


def normalize(value: str) -> tuple[str | None, str | None]:
    """Return (isbn_10, isbn_13) from any ISBN string."""
    clean = value.replace("-", "").replace(" ", "")
    if not (isbnlib.is_isbn10(clean) or isbnlib.is_isbn13(clean)):
        return None, None
    isbn_13 = to_isbn13(clean)
    isbn_10 = to_isbn10(clean)
    return isbn_10, isbn_13
