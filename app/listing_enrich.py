"""Fetch listing facts from Booli (broker link) and mäklare pages."""

from __future__ import annotations

import html as html_lib
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
FETCH_DELAY_SECONDS = 1.5

BOOLI_HOST = "booli.se"
BROKER_LINK_PATTERNS = (
    re.compile(r"läs\s+mer\s+hos\s+(?:mäklaren|säljaren)", re.I),
    re.compile(r"besök\s+mäklaren", re.I),
    re.compile(r"hos\s+mäklaren", re.I),
)


@dataclass
class ListingFacts:
    address: str | None = None
    price: int | None = None
    rooms: float | None = None
    area_sqm: float | None = None
    monthly_fee: int | None = None
    floor: int | None = None
    broker_url: str | None = None


@dataclass
class EnrichResult:
    listing_id: int
    ok: bool
    reason: str | None = None
    facts: ListingFacts = field(default_factory=ListingFacts)
    updated_fields: list[str] = field(default_factory=list)


class FetchError(Exception):
    def __init__(self, code: str, message: str, http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def is_booli_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return False
    return BOOLI_HOST in host


def find_booli_url_in_text(text: str | None) -> str | None:
    if not text:
        return None
    for match in re.finditer(r"https?://(?:www\.)?booli\.se/(?:annons|bostad)/\d+", text, re.I):
        return match.group(0)
    return None


def _decode_html_text(value: str) -> str:
    return html_lib.unescape(value).replace("\xa0", " ").strip()


def parse_swedish_int(text: str | None) -> int | None:
    if not text:
        return None
    cleaned = _decode_html_text(text)
    cleaned = cleaned.replace("kr", "").replace("SEK", "").strip()
    cleaned = re.sub(r"[^\d]", "", cleaned)
    if not cleaned:
        return None
    return int(cleaned)


def parse_swedish_float(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = _decode_html_text(text)
    cleaned = cleaned.replace("kvm", "").replace("m²", "").replace("m2", "").strip()
    cleaned = cleaned.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def fetch_url(url: str, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 30.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        code = "booli_blocked" if BOOLI_HOST in url and exc.code == 403 else "http_error"
        raise FetchError(code, f"HTTP {exc.code} for {url}", http_status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise FetchError("network_error", str(exc.reason)) from exc


def extract_broker_url_from_booli_html(html: str, page_url: str) -> str | None:
    """Find mäklare CTA link in Booli HTML."""
    base = page_url
    # Prefer anchors whose visible text matches broker CTA phrases.
    for anchor in re.finditer(
        r'<a\b([^>]*?)href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>',
        html,
        re.I | re.S,
    ):
        attrs_before, href, attrs_after, inner = anchor.groups()
        text = re.sub(r"<[^>]+>", " ", inner)
        text = _decode_html_text(text)
        combined_attrs = f"{attrs_before} {attrs_after}"
        label = text or _decode_html_text(re.sub(r'.*aria-label=["\']([^"\']+)["\'].*', r"\1", combined_attrs, flags=re.I))
        if not any(pat.search(label) for pat in BROKER_LINK_PATTERNS):
            if not any(pat.search(combined_attrs) for pat in BROKER_LINK_PATTERNS):
                continue
        absolute = urllib.parse.urljoin(base, href)
        if is_booli_url(absolute):
            continue
        if absolute.startswith(("http://", "https://")):
            return absolute

    # Fallback: external links in broker sections (class/data attributes).
    for match in re.finditer(r'href=["\'](https?://[^"\']+)["\']', html, re.I):
        href = match.group(1)
        if is_booli_url(href):
            continue
        if any(
            token in href.lower()
            for token in (
                "lansfast",
                "maklarhuset",
                "notar",
                "svenskfast",
                "fastighetsbyran",
                "mäklar",
                "maklar",
                "erikolsson",
                "bostadsratterna",
            )
        ):
            return href
    return None


def _iter_json_ld_objects(html: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = block.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            objects.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            objects.append(data)
    return objects


def _facts_from_json_ld(obj: dict[str, Any], facts: ListingFacts) -> None:
    obj_type = obj.get("@type") or ""
    types = obj_type if isinstance(obj_type, list) else [obj_type]
    type_str = " ".join(str(t) for t in types).lower()

    if not facts.address and obj.get("name"):
        facts.address = _decode_html_text(str(obj["name"]))

    offers = obj.get("offers")
    if isinstance(offers, dict):
        offers = [offers]
    if isinstance(offers, list):
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            price = offer.get("price")
            if facts.price is None and price is not None:
                facts.price = parse_swedish_int(str(price))

    desc = obj.get("description")
    if isinstance(desc, str):
        if facts.rooms is None:
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*rum", desc, re.I)
            if m:
                facts.rooms = parse_swedish_float(m.group(1))
        if facts.area_sqm is None:
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|kvm)", desc, re.I)
            if m:
                facts.area_sqm = parse_swedish_float(m.group(1))

    for key in ("description1", "description2"):
        val = obj.get(key)
        if not isinstance(val, str):
            continue
        if facts.rooms is None:
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*rum", val, re.I)
            if m:
                facts.rooms = parse_swedish_float(m.group(1))
        if facts.area_sqm is None:
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|kvm)?", val, re.I)
            if m and "rum" not in val.lower():
                facts.area_sqm = parse_swedish_float(m.group(1))

    if "apartment" in type_str or "product" in type_str or "residence" in type_str:
        if facts.area_sqm is None and obj.get("floorSize"):
            facts.area_sqm = parse_swedish_float(str(obj.get("floorSize")))
        if facts.rooms is None and obj.get("numberOfRooms"):
            facts.rooms = parse_swedish_float(str(obj.get("numberOfRooms")))


def _facts_from_label_patterns(html: str, facts: ListingFacts) -> None:
    text = _decode_html_text(re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    patterns: list[tuple[str, str]] = [
        (r"(?:utgångspris|pris|utropspris)\s*[:\s]*([\d\s\xa0]+)\s*kr", "price"),
        (r"(?:månadsavgift|avgift)\s*[:\s]*([\d\s\xa0]+)\s*kr", "monthly_fee"),
        (r"(?:antal\s+)?rum\s*[:\s]*(\d+(?:[.,]\d+)?)", "rooms"),
        (r"(?:boarea|yta|boyta)\s*[:\s]*(\d+(?:[.,]\d+)?)\s*(?:m²|kvm|m2)?", "area_sqm"),
        (r"våning\s*[:\s]*(\d+)", "floor"),
    ]
    for pattern, field_name in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        raw = match.group(1)
        if field_name == "price" and facts.price is None:
            facts.price = parse_swedish_int(raw)
        elif field_name == "monthly_fee" and facts.monthly_fee is None:
            facts.monthly_fee = parse_swedish_int(raw)
        elif field_name == "rooms" and facts.rooms is None:
            facts.rooms = parse_swedish_float(raw)
        elif field_name == "area_sqm" and facts.area_sqm is None:
            facts.area_sqm = parse_swedish_float(raw)
        elif field_name == "floor" and facts.floor is None:
            facts.floor = parse_swedish_int(raw)


def parse_broker_html(html: str, page_url: str) -> ListingFacts:
    facts = ListingFacts(broker_url=page_url)
    for obj in _iter_json_ld_objects(html):
        graph = obj.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    _facts_from_json_ld(item, facts)
        _facts_from_json_ld(obj, facts)

    og_price = re.search(
        r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if og_price and facts.price is None:
        facts.price = parse_swedish_int(og_price.group(1))

    _facts_from_label_patterns(html, facts)
    return facts


def resolve_broker_url(
    listing: dict[str, Any],
    fetch_html: Any | None = None,
) -> tuple[str | None, str | None]:
    """Return (broker_url, failure_reason). fetch_html(url) -> html string."""
    fetch_html = fetch_html or fetch_url
    url = listing.get("url")
    notes = listing.get("notes")

    if url and not is_booli_url(url):
        return url, None

    booli_url = url if is_booli_url(url) else find_booli_url_in_text(notes)
    if not booli_url:
        return None, "no_booli_url"

    try:
        html = fetch_html(booli_url)
    except FetchError as exc:
        return None, exc.code

    broker = extract_broker_url_from_booli_html(html, booli_url)
    if not broker:
        return None, "no_broker_link"
    return broker, None


def enrich_listing_row(
    listing: dict[str, Any],
    *,
    fetch_html: Any | None = None,
    only_missing_price: bool = True,
) -> EnrichResult:
    listing_id = int(listing["id"])
    if only_missing_price and listing.get("price") is not None:
        return EnrichResult(listing_id=listing_id, ok=False, reason="already_has_price")

    fetch_html = fetch_html or fetch_url
    broker_url, resolve_reason = resolve_broker_url(listing, fetch_html=fetch_html)
    if not broker_url:
        return EnrichResult(listing_id=listing_id, ok=False, reason=resolve_reason or "no_broker_url")

    try:
        html = fetch_html(broker_url)
    except FetchError as exc:
        return EnrichResult(
            listing_id=listing_id,
            ok=False,
            reason=f"broker_{exc.code}",
            facts=ListingFacts(broker_url=broker_url),
        )

    facts = parse_broker_html(html, broker_url)
    facts.broker_url = broker_url
    return EnrichResult(listing_id=listing_id, ok=True, facts=facts)


def apply_enrich_result(
    conn: sqlite3.Connection,
    listing: dict[str, Any],
    result: EnrichResult,
) -> list[str]:
    if not result.ok:
        return []

    facts = result.facts
    updates: dict[str, Any] = {}
    updated_fields: list[str] = []

    def set_if_missing(field: str, value: Any) -> None:
        if value is None:
            return
        if listing.get(field) is not None and field != "url":
            return
        updates[field] = value
        updated_fields.append(field)

    set_if_missing("address", facts.address if not (listing.get("address") or "").startswith("Booli ") else None)
    set_if_missing("price", facts.price)
    set_if_missing("rooms", facts.rooms)
    set_if_missing("area_sqm", facts.area_sqm)
    set_if_missing("monthly_fee", facts.monthly_fee)
    set_if_missing("floor", facts.floor)

    if facts.broker_url:
        old_url = listing.get("url")
        if old_url != facts.broker_url:
            updates["url"] = facts.broker_url
            updated_fields.append("url")
            if is_booli_url(old_url):
                note_line = f"Booli: {old_url}"
                notes = listing.get("notes") or ""
                if note_line not in notes:
                    updates["notes"] = (notes + "\n" + note_line).strip() if notes else note_line
                    updated_fields.append("notes")

    if not updates:
        return []

    columns = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE listings SET {columns} WHERE id = ?",
        list(updates.values()) + [listing["id"]],
    )
    conn.commit()
    result.updated_fields = updated_fields
    return updated_fields


def select_listings_for_enrich(
    conn: sqlite3.Connection,
    *,
    listing_id: int | None = None,
    interest: str | None = None,
    all_missing: bool = False,
) -> list[dict[str, Any]]:
    if listing_id is not None:
        row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return [dict(row)] if row else []

    clauses = []
    params: list[Any] = []
    if all_missing or interest:
        clauses.append("price IS NULL")
    if interest:
        clauses.append("interest = ?")
        params.append(interest)
    where = " AND ".join(clauses) if clauses else "1=1"
    rows = conn.execute(
        f"SELECT * FROM listings WHERE {where} ORDER BY created_at DESC, id DESC",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def run_enrich_batch(
    conn: sqlite3.Connection,
    listings: list[dict[str, Any]],
    *,
    fetch_html: Any | None = None,
    sleep_seconds: float = FETCH_DELAY_SECONDS,
) -> list[EnrichResult]:
    fetch_html = fetch_html or fetch_url
    results: list[EnrichResult] = []
    for idx, listing in enumerate(listings):
        if idx > 0 and sleep_seconds:
            time.sleep(sleep_seconds)
        result = enrich_listing_row(listing, fetch_html=fetch_html)
        if result.ok:
            apply_enrich_result(conn, listing, result)
        results.append(result)
    return results
