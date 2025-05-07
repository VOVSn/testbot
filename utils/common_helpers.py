import re

def normalize_test_id(raw_id) -> str:
    """
    Normalizes a test ID by removing 'test' prefix (case-insensitive),
    underscores, and converting to lowercase. Returns empty string if
    input is None or empty.
    """
    if not raw_id:
        return ""
    # Remove 'test' prefix (case-insensitive)
    normalized = re.sub(r'^test', '', raw_id, flags=re.IGNORECASE)
    # Remove underscores
    normalized = normalized.replace('_', '')
    # Convert to lowercase and strip whitespace
    return normalized.lower().strip()