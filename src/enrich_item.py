import logging
import re
from typing import Dict, Set

from src.title_parser import parse_title
from src.utils import is_precise_substring_match

logger = logging.getLogger(__name__)

generic_terms = {'CELERON', 'PENTIUM', 'ATOM', 'XEON', 'RYZEN', 'ATHLON'}

def enrich_item(
    item: Dict,
    passmark_scores: Dict[str, int],
    idle_power_data: Dict[str, float],
    cpus_not_found_in_passmark: Set[str],
    cpus_not_found_in_idle: Set[str],
) -> Dict:
    """Return an enriched listing dict ready for JSON serialisation."""

    title = item.get('title', '')
    parsed = parse_title(title)
    cpu_model_str = parsed['cpu_model']
    is_generic_intel_core_type = parsed['is_generic_intel_core_type']
    generic_intel_core_type = parsed['generic_intel_core_type']
    ram = parsed['ram']
    storage = parsed['storage']

    # ------------------- Benchmarks look-up ------------------------------
    performance_score = None
    idle_watts = None

    can_score = (
        cpu_model_str not in ('N/A', 'None')
        and not is_generic_intel_core_type
        and cpu_model_str not in generic_terms
    )

    if can_score:
        performance_score = passmark_scores.get(cpu_model_str)

        # Special handling for N-series
        if not performance_score and cpu_model_str.startswith('N'):
            performance_score = passmark_scores.get(f'INTEL {cpu_model_str}')

        # Fallback substring search
        if not performance_score:
            for key, val in passmark_scores.items():
                if is_precise_substring_match(cpu_model_str, key):
                    performance_score = val
                    break

        if not performance_score:
            cpus_not_found_in_passmark.add(cpu_model_str)

        # Idle power look-up
        idle_watts = idle_power_data.get(cpu_model_str) or idle_power_data.get(
            f'INTEL {cpu_model_str}'
        )
        if not idle_watts:
            for key, val in idle_power_data.items():
                if is_precise_substring_match(cpu_model_str, key):
                    idle_watts = val
                    break
        if not idle_watts:
            cpus_not_found_in_idle.add(cpu_model_str)

    # ---------------------- Misc fields ----------------------------------
    price_val = None
    price_raw = item.get('price', {}).get('value')
    if price_raw:
        try:
            price_val = float(price_raw)
        except ValueError:
            logger.debug("Could not parse price '%s'", price_raw)

    free_shipping = False
    for opt in item.get('shippingOptions', []) or []:
        free_shipping = opt.get('freeShipping') in (True, 'true', 'True')
        if free_shipping:
            break

    cpu_type_display = (
        generic_intel_core_type
        if generic_intel_core_type and generic_intel_core_type != 'None'
        else (
            'N-SERIES'
            if cpu_model_str.startswith('N')
            else (
                'AMD'
                if cpu_model_str in {'RYZEN', 'ATHLON'}
                else ('None' if cpu_model_str == 'None' else 'OTHER')
            )
        )
    )

    return {
        'title': item.get('title'),
        'price': price_val,
        'cpu_type': cpu_type_display,
        'cpu_model': cpu_model_str,
        'ram': ram,
        'storage': storage,
        'performance': performance_score,
        'free_shipping': free_shipping,
        'tco': None,
        'performance_per_dollar': None,
        'item_url': item.get('itemWebUrl'),
        'image_url': item.get('image', {}).get('imageUrl'),
        'cpu_idle_power': idle_watts,
        'itemId': item.get('itemId'),
    } 