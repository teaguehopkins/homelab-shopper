import logging
import re
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


def _parse_capacity_to_gb(capacity_str: str) -> int:
    """Convert strings like '8GB', '1TB' to integer GB. Returns 0 when unknown."""
    if not capacity_str or capacity_str.upper() == 'N/A':
        return 0
    capacity_str = capacity_str.upper()
    match = re.search(r"(\d+\.\d+|\d+)", capacity_str)
    if not match:
        return 0
    val = float(match.group(1))
    if 'TB' in capacity_str:
        val *= 1024
    return int(val)


def calculate_tco_and_perf(item: Dict, assumptions: Dict) -> Tuple[float, float]:
    """Return (tco, performance_per_dollar) following the same rules as frontend JS.

    item: enriched listing dict from enrich_item (contains price, cpu_idle_power, etc.)
    assumptions: dict from config['app']['tco_assumptions']
    """
    if item.get('cpu_idle_power') in (None, '') or item.get('price') in (None, ''):
        return None, None

    price = float(item['price'])
    idle_watts = float(item['cpu_idle_power'])

    kwh_cost = float(assumptions.get('kwh_cost', 0.14))
    lifespan_years = max(int(assumptions.get('lifespan_years', 5)), 1)

    energy_cost = (idle_watts / 1000) * 24 * 365 * lifespan_years * kwh_cost

    # shipping
    shipping_cost = 0.0
    if not item.get('free_shipping'):
        if str(item.get('cpu_model', '')).upper().endswith('T'):
            shipping_cost = float(assumptions.get('shipping_cost_t_cpu', 10))
        else:
            shipping_cost = float(assumptions.get('shipping_cost_non_t_cpu', 35))

    # RAM shortfall
    item_ram_gb = _parse_capacity_to_gb(item.get('ram'))
    required_ram = float(assumptions.get('required_ram_gb', 16))
    ram_shortfall_cost = float(assumptions.get('ram_upgrade_flat_cost', 30)) if item_ram_gb < required_ram else 0.0

    # Storage shortfall
    item_storage_gb = _parse_capacity_to_gb(item.get('storage'))
    required_storage = float(assumptions.get('required_storage_gb', 128))
    storage_shortfall_cost = float(assumptions.get('storage_upgrade_flat_cost', 15)) if item_storage_gb < required_storage else 0.0

    # AC adapter assumed included for automated job
    ac_adapter_cost = 0.0

    tco = price + energy_cost + shipping_cost + ram_shortfall_cost + storage_shortfall_cost + ac_adapter_cost

    perf = item.get('performance')
    perf_per_dollar = (float(perf) / tco) if perf and tco > 0 else None

    return tco, perf_per_dollar 