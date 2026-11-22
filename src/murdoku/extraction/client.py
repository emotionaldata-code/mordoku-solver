"""HTTP access restricted to original public Murdoku JSON resources."""

import re
from urllib.parse import urlparse

import httpx
from pydantic import JsonValue, TypeAdapter

from .raw import RAW_ADAPTER, RawPuzzle

BASE_URL = "https://murdoku.com/play_puzzles"


def puzzle_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "murdoku.com":
        raise ValueError("Expected an https://murdoku.com/play/puzzle-... URL")
    match = re.fullmatch(r"/play/(puzzle-[a-z0-9-]+)/?", parsed.path)
    if match is None or parsed.query or parsed.fragment:
        raise ValueError("Invalid puzzle URL path")
    return match[1]


def fetch(url: str, *, client: httpx.Client | None = None) -> RawPuzzle:
    identifier = puzzle_id(url)
    if client is None:
        with httpx.Client(timeout=30, follow_redirects=False) as owned:
            return fetch(url, client=owned)
    response = client.get(f"{BASE_URL}/en/{identifier}.json")
    response.raise_for_status()
    return RAW_ADAPTER.validate_json(response.content)


def fetch_catalog(*, client: httpx.Client | None = None) -> JsonValue:
    if client is None:
        with httpx.Client(timeout=30, follow_redirects=False) as owned:
            return fetch_catalog(client=owned)
    response = client.get(f"{BASE_URL}/_puzzleCatalog.json")
    response.raise_for_status()
    return TypeAdapter(JsonValue).validate_json(response.content)
