import logging

logger = logging.getLogger(__name__)

def is_precise_substring_match(search_term: str, text: str) -> bool:
    """Return True if `search_term` appears in `text` and the following
    character (if any) is **not** alphanumeric.
    """
    try:
        idx = text.find(search_term)
        if idx == -1:
            return False
        if idx + len(search_term) == len(text):
            return True
        return not text[idx + len(search_term)].isalnum()
    except Exception as exc:  # pragma: no cover
        logger.error("Error in is_precise_substring_match: %s", exc)
        return False 