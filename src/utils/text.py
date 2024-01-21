import unicodedata
from typing import List


def clean_html_text(text: str) -> str:
    """
    Normalize unicode text.
    """
    return unicodedata.normalize("NFKD", text).strip()


def strip_line_escape(body: List[str]) -> List[str]:
    """
    Remove leading and trailing line break from a list of string.
    """
    while len(body) > 0 and (body[-1] == "\n" or body[-1] == ""):
        body.pop()
    while len(body) > 0 and (body[0] == "\n" or body[0] == ""):
        body.pop(0)

    return body
