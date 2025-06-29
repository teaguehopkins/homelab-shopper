"""Domain-level helpers shared by both the Flask route and the daily alert.

These functions are *pure* – they take ordinary Python data, perform the
search/enrichment/TCO math and return data.  No HTTP or e-mail concerns are
handled here, keeping the code testable and reusable.
"""

from __future__ import annotations

from typing import Any, List, Tuple

from src.ebay_api import EBayAPI
from src.data_loader import PASSMARK_SCORES, IDLE_POWER_DATA
from src.enrich_item import enrich_item
from src.tco import calculate_tco_and_perf


def find_listings(
    config: dict[str, Any],
    *,
    full_search_override: bool | None = None,
) -> Tuple[List[dict], int]:
    """Run eBay searches as configured and return enriched listings.

    Returns (listings, total_reported_by_api).
    Raises RuntimeError on authentication failure.
    """

    search_cfg = config["search"]
    keywords: str = search_cfg["keywords"]
    category_id = search_cfg["category_id"]
    max_price = search_cfg["max_price"]
    full_search = (
        full_search_override
        if full_search_override is not None
        else search_cfg.get("full_search", False)
    )

    # --- Authenticate --------------------------------------------------
    api = EBayAPI(
        app_id=config["ebay"]["app_id"],
        cert_id=config["ebay"]["cert_id"],
        sandbox=config["ebay"].get("sandbox", False),
    )

    if not api.get_oauth_token():
        raise RuntimeError("Failed to authenticate with eBay API")

    # --- Perform search -------------------------------------------------
    search_terms = [t.strip() for t in keywords.split(",") if t.strip()]
    all_results: list[dict] = []
    seen_ids: set[str] = set()
    total_items_found_api = 0

    cpus_not_found_passmark: set[str] = set()
    cpus_not_found_idle: set[str] = set()

    for term in search_terms:
        items, term_total = api.search_items(term, category_id, max_price, full_search)
        total_items_found_api += term_total
        for item in items:
            item_id = item.get("itemId")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            processed = enrich_item(
                item,
                PASSMARK_SCORES,
                IDLE_POWER_DATA,
                cpus_not_found_passmark,
                cpus_not_found_idle,
            )
            all_results.append(processed)

    return all_results, total_items_found_api


def apply_tco(listings: List[dict], tco_cfg: dict[str, Any] | None) -> None:
    """Compute TCO/performance-per-dollar for each listing *in-place*."""

    if tco_cfg is None:
        tco_cfg = {}

    for listing in listings:
        tco, perf_per_dollar = calculate_tco_and_perf(listing, tco_cfg)
        listing["tco"] = tco
        listing["performance_per_dollar"] = perf_per_dollar