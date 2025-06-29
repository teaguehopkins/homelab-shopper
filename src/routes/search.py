import json
import logging
from flask import Blueprint, jsonify, Response

from src.config import load_config
from src.search_service import find_listings, apply_tco

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)

@search_bp.route('/search', methods=['POST'])
def search():  # noqa: C901 – function is complex; TODO split later
    """Perform searches for each keyword and combine results."""
    config = load_config()
    logger.info("Loaded configuration")

    # ---- Perform search & enrichment via shared service -------------------
    try:
        listings, total_items_found_api = find_listings(config)
    except RuntimeError as exc:
        logger.error("Search failed: %s", exc)
        return jsonify({'status': 'error', 'message': str(exc)}), 500

    # Apply TCO/performance calculations
    tco_cfg = config.get('app', {}).get('tco_assumptions', {})
    apply_tco(listings, tco_cfg)

    # Prepare defaults for frontend form fields
    tco_defaults_for_frontend = {
        'kwh_cost': tco_cfg.get('kwh_cost', 0.1),
        'lifespan_years': tco_cfg.get('lifespan_years', 5),
        'shipping_cost_t_cpu': tco_cfg.get('shipping_cost_t_cpu', 10),
        'shipping_cost_non_t_cpu': tco_cfg.get('shipping_cost_non_t_cpu', 35),
        'required_ram_gb': tco_cfg.get('required_ram_gb', 16),
        'ram_upgrade_flat_cost': tco_cfg.get('ram_upgrade_flat_cost', 30),
        'required_storage_gb': tco_cfg.get('required_storage_gb', 128),
        'storage_upgrade_flat_cost': tco_cfg.get('storage_upgrade_flat_cost', 15),
    }

    response_body = json.dumps({
        'status': 'success',
        'listings': listings,
        'total_found': total_items_found_api,
        'actually_processed': len(listings),
        'full_search_enabled': config['search'].get('full_search', False),
        'tco_defaults': tco_defaults_for_frontend,
    })

    return Response(response_body, mimetype="application/json", direct_passthrough=True)

    # No explicit broad exception handling; errors propagate to app-level handlers 