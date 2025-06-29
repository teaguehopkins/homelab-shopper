import logging
import os
from typing import List
import requests
from jinja2 import Template

from src.config import load_config
from src.search_service import find_listings, apply_tco

logger = logging.getLogger(__name__)

MAILGUN_API_BASE = "https://api.mailgun.net/v3"


def _send_email_via_mailgun(subject: str, text_body: str, recipients: List[str], html_body: str = None) -> None:
    """Send an email using Mailgun HTTP API.

    Requires environment variables:
    MAILGUN_API_KEY – your private API key
    MAILGUN_DOMAIN  – domain configured in Mailgun (e.g. mg.example.com)
    """
    api_key = os.getenv("MAILGUN_API_KEY")
    domain = os.getenv("MAILGUN_DOMAIN")

    if not api_key or not domain:
        logger.error("Mailgun credentials not configured (MAILGUN_API_KEY / MAILGUN_DOMAIN)")
        return

    url = f"{MAILGUN_API_BASE}/{domain}/messages"
    data = {
        "from": f"Homelab Deal Finder <alerts@{domain}>",
        "to": recipients,
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        data["html"] = html_body

    logger.info("Sending alert email to %s via Mailgun", ", ".join(recipients))
    resp = requests.post(url, auth=("api", api_key), data=data, timeout=15)
    try:
        resp.raise_for_status()
        logger.info("Mailgun response: %s", resp.json())
    except requests.RequestException as exc:
        logger.error("Failed to send Mailgun email: %s", exc)


def run_daily_search_and_alert() -> None:
    """Run eBay search, filter by perf-per-dollar, email alerts."""
    config = load_config()

    perf_threshold: float = config.get("alerts", {}).get("perf_per_dollar_min", 0)
    recipients: List[str] = config.get("alerts", {}).get("recipients", [])
    if not recipients:
        logger.warning("No alert recipients configured; skipping email send.")

    # Retrieve and enrich listings (use lighter one-page search)
    try:
        listings, _ = find_listings(config, full_search_override=False)
    except RuntimeError as exc:
        logger.error("Cannot run daily alert – %s", exc)
        return

    # Compute TCO/performance
    apply_tco(listings, config.get("app", {}).get("tco_assumptions", {}))

    # Filter by performance threshold
    good_items = [it for it in listings if (it.get("performance_per_dollar") or 0) >= perf_threshold]

    if not good_items:
        logger.info("No items exceeded perf/$ threshold %.2f today", perf_threshold)
        return

    good_items.sort(key=lambda x: x["performance_per_dollar"], reverse=True)

    def _build_plain(items):
        header = "Perf/$  | Price  | CPU Model | RAM | Storage | URL\n" + "-"*90
        rows = [
            f"{it['performance_per_dollar']:.1f}   | ${it['price']:.2f} | {it['cpu_model']:<10} | {it['ram']:<6} | {it['storage']:<8} | {it['item_url']}"
            for it in items
        ]
        return "\n".join([header, *rows])

    def _build_html(items):
        """Render HTML using a lightweight Jinja2 template instead of
        manually concatenating strings.
        """
        template_str = """
        <html><body>
        <h3>Homelab Deal Alerts</h3>
        <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">
            <thead>
                <tr style="background:#f2f2f2">
                    <th>Perf/$</th><th>Price</th><th>CPU</th><th>RAM</th><th>Storage</th><th>Link</th>
                </tr>
            </thead>
            <tbody>
            {% for it in items %}
                <tr>
                    <td>{{ '%.1f' % it.performance_per_dollar }}</td>
                    <td>${{ '%.2f' % it.price }}</td>
                    <td>{{ it.cpu_model }}</td>
                    <td>{{ it.ram }}</td>
                    <td>{{ it.storage }}</td>
                    <td><a href="{{ it.item_url }}">link</a></td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        </body></html>
        """
        return Template(template_str).render(items=items)

    body_text = _build_plain(good_items)
    body_html = _build_html(good_items)

    _send_email_via_mailgun(
        subject="Homelab Deal Alert – New high Perf/$ listings",
        text_body=body_text,
        html_body=body_html,
        recipients=recipients,
    )


if __name__ == "__main__":
    from src.logging_setup import configure as _configure_logging

    _configure_logging()
    run_daily_search_and_alert() 