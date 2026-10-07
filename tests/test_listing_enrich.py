from pathlib import Path

import pytest

from app.listing_enrich import (
    extract_broker_url_from_booli_html,
    parse_broker_html,
    parse_swedish_int,
    resolve_broker_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_swedish_int_nbsp():
    assert parse_swedish_int("3\u00a0495\u00a0000 kr") == 3_495_000


def test_extract_broker_link_from_booli_fixture():
    html = (FIXTURES / "booli_annons_broker_link.html").read_text(encoding="utf-8")
    url = extract_broker_url_from_booli_html(html, "https://www.booli.se/annons/6252361")
    assert url == "https://www.lansfast.se/till-salu/test/landavagen-77/abc123/"


def test_parse_lansfast_json_ld_and_labels():
    html = (FIXTURES / "lansfast_product.jsonld.html").read_text(encoding="utf-8")
    facts = parse_broker_html(html, "https://www.lansfast.se/till-salu/test/")
    assert facts.price == 3_495_000
    assert facts.rooms == 3
    assert facts.area_sqm == 76
    assert facts.monthly_fee == 5927
    assert facts.floor == 2
    assert facts.address == "Diligensvägen 4"


def test_resolve_broker_skips_booli_blocked():
    from app.listing_enrich import FetchError

    listing = {"url": "https://www.booli.se/annons/1", "notes": None}

    def fetch_fail(url: str) -> str:
        raise FetchError("booli_blocked", "HTTP 403", http_status=403)

    broker, reason = resolve_broker_url(listing, fetch_html=fetch_fail)
    assert broker is None
    assert reason == "booli_blocked"


def test_resolve_broker_from_booli_fixture():
    listing = {"url": "https://www.booli.se/annons/6252361", "notes": None}
    html = (FIXTURES / "booli_annons_broker_link.html").read_text(encoding="utf-8")

    def fetch(url: str) -> str:
        if "booli" in url:
            return html
        return (FIXTURES / "lansfast_product.jsonld.html").read_text(encoding="utf-8")

    broker, reason = resolve_broker_url(listing, fetch_html=fetch)
    assert reason is None
    assert broker and "lansfast" in broker
