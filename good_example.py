"""Small utility for Gemma PR Swarm: safe diff size formatting."""
import os


def format_diff_size(additions: int, deletions: int) -> str:
    """Return a short human-readable summary like '+12 / -3'."""
    return f"+{additions} / -{deletions}"


def get_api_key() -> str:
    """Read the Gemini key from the environment, never from source code."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return key


def test_format_diff_size():
    assert format_diff_size(12, 3) == "+12 / -3"
    assert format_diff_size(0, 0) == "+0 / -0"
