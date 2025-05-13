"""
Web application module for the Homelab Deal Finder.
"""
import logging
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from src.ebay_api import EBayAPI
from src.config import load_config
import re
import time
import requests # Import the requests library

# Configure logging
logger = logging.getLogger(__name__)

def parse_capacity_to_gb(capacity_str):
    """Converts a capacity string (e.g., '8GB', '1TB', 'N/A') to GB.
       Returns 0 if 'N/A', unparseable, or None."""
    if not capacity_str or capacity_str.upper() == 'N/A':
        return 0
    
    capacity_str = capacity_str.upper()
    num_part = re.findall(r'\d+\.\d+|\d+', capacity_str) # Extracts numbers, including decimals
    
    if not num_part:
        return 0
        
    try:
        val = float(num_part[0])
        if 'TB' in capacity_str:
            return int(val * 1024)
        elif 'GB' in capacity_str:
            return int(val)
        else: # Assume GB if no unit, but this is less certain
            logger.warning(f"Capacity string '{capacity_str}' has no clear unit (GB/TB), assuming GB for {val}.")
            return int(val) 
    except ValueError:
        return 0

def is_precise_substring_match(search_term, text_from_file):
    """Checks if search_term is a substring of text_from_file and ensures the match is precise,
       meaning the character following the match (if any) is not alphanumeric."""
    try:
        start_index = text_from_file.find(search_term)
        if start_index == -1:
            return False  # Not a substring

        # Check if the match is at the very end of the text_from_file
        if start_index + len(search_term) == len(text_from_file):
            return True  # Valid match if it's at the end

        # If not at the end, get the character immediately following the search_term
        char_after_match = text_from_file[start_index + len(search_term)]

        # If the character after the match is NOT alphanumeric, it's a valid precise match
        if not char_after_match.isalnum():
            return True
        else:
            # e.g., search_term "I5-9500" in text_from_file "I5-9500T" - char_after_match is 'T' (alphanumeric)
            return False
            
    except Exception as e:
        logger.error(f"Error in is_precise_substring_match: {e}")
        return False

# Load PassMark data once at startup
passmark_scores = {}
def load_passmark_data(filepath='passmark.txt'):
    """Loads PassMark data from the specified file."""
    start_time = time.time()
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    cpu_name = parts[0].strip().upper() # Normalize key
                    try:
                        score = int(parts[1].replace(',', '').strip())
                        passmark_scores[cpu_name] = score
                        count += 1
                    except ValueError:
                        logger.warning(f"Could not parse score for CPU '{parts[0]}': '{parts[1]}'")
                # Add more robust parsing if needed, e.g., handle lines without tabs
    except FileNotFoundError:
        logger.error(f"PassMark file not found at '{filepath}'")
    except Exception as e:
        logger.error(f"Error loading PassMark data: {e}", exc_info=True)
    
    end_time = time.time()
    logger.info(f"Loaded {count} PassMark scores from '{filepath}' in {end_time - start_time:.2f} seconds.")

load_passmark_data()

# Load Idle Power data once at startup
idle_power_data = {}
def load_idle_power_data(filepath='idlepower.txt'):
    """Loads CPU idle power data from the specified file."""
    start_time = time.time()
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Skip header line
            next(f, None) 
            for line in f:
                line_content = line.strip()
                if not line_content: # Skip empty lines
                    continue

                # Try to match pattern: (CPU Name Part) (Whitespace) (Numeric Power Value Part)
                # This assumes the power value is the last numeric part on the line.
                match = re.match(r"^(.*?)(\s+[\d\.]+)$", line_content)
                
                if match:
                    cpu_name_str = match.group(1).strip() # Captured CPU name part
                    power_str = match.group(2).strip()    # Captured power value string (e.g., "6.5")
                    
                    cpu_name_key = cpu_name_str.upper()
                    try:
                        power_watts = float(power_str)
                        idle_power_data[cpu_name_key] = power_watts
                        count += 1
                    except ValueError:
                        logger.warning(f"Could not parse idle power value '{power_str}' for CPU '{cpu_name_str}' from line: '{line_content}'")
                else:
                    # Log lines that don't match the expected "name then number" pattern,
                    # but only if it's not an empty or obviously non-data line.
                    if line_content: # Avoid logging warnings for blank lines if any slip through
                        logger.warning(f"Line format not recognized in idlepower.txt, could not extract CPU name and power: '{line_content}'")
    except FileNotFoundError:
        logger.error(f"Idle power file not found at '{filepath}'")
    except Exception as e:
        logger.error(f"Error loading idle power data: {e}", exc_info=True)
    
    end_time = time.time()
    logger.info(f"Loaded {count} idle power entries from '{filepath}' in {end_time - start_time:.2f} seconds.")

load_idle_power_data()

# Initialize Flask application
app = Flask(__name__, template_folder='../templates')

# Add custom Jinja2 filter for formatting prices
@app.template_filter('price')
def format_price(value):
    if value is None:
        return 'N/A'
    return f'${value:,.2f}'

@app.route('/')
def index():
    """Render the main page."""
    config = load_config() # Load config to get full_search setting
    full_search_enabled = config.get('search', {}).get('full_search', False)
    return render_template('index.html', listings=[], full_search_enabled=full_search_enabled)

@app.route('/search', methods=['POST'])
def search():
    """Perform searches for each keyword and combine results."""
    try:
        # Load configuration
        config = load_config()
        logger.info("Loaded configuration")
        
        # Debug environment variables
        logger.info(f"Environment variables:")
        logger.info(f"EBAY_CLIENT_ID: {'*' * len(os.getenv('EBAY_CLIENT_ID', '')) if os.getenv('EBAY_CLIENT_ID') else 'Not set'}")
        logger.info(f"EBAY_CLIENT_SECRET: {'*' * len(os.getenv('EBAY_CLIENT_SECRET', '')) if os.getenv('EBAY_CLIENT_SECRET') else 'Not set'}")
        
        # Initialize eBay API
        api = EBayAPI(
            app_id=config['ebay']['app_id'],
            cert_id=config['ebay']['cert_id'],
            sandbox=config['ebay'].get('sandbox', False)
        )
        logger.info("Initialized eBay API")
        
        # Get OAuth token using client credentials
        logger.info("Getting OAuth token for the application...")
        if not api.get_oauth_token():
            logger.error("Failed to get OAuth token for the application")
            return jsonify({'status': 'error', 'message': 'Failed to authenticate with eBay'}), 500
        else:
            logger.info("Successfully obtained application OAuth token!")
        
        # Get search parameters from config
        keywords = config['search']['keywords']
        category_id = config['search']['category_id']
        max_price = config['search']['max_price']
        full_search = config['search'].get('full_search', False)
        logger.info(f"Search parameters: keywords={keywords}, category_id={category_id}, max_price={max_price}, full_search={full_search}")
        
        # Split keywords and search for each one
        search_terms = [term.strip() for term in keywords.split(',')]
        all_results = []
        seen_item_ids = set()
        total_items_found_api = 0 # Initialize total counter
        cpus_not_found_in_passmark = set()  # Initialize set for missing PassMark CPUs
        cpus_not_found_in_idlepower = set() # Initialize set for missing Idle Power CPUs
        
        # Get TCO assumptions from config
        tco_config = config.get('app', {}).get('tco_assumptions', {})
        
        kwh_cost = tco_config.get('kwh_cost', 0.1)
        lifespan_years = tco_config.get('lifespan_years', 5)
        shipping_t_cpu = tco_config.get('shipping_cost_t_cpu', 10)
        shipping_non_t_cpu = tco_config.get('shipping_cost_non_t_cpu', 35)
        required_ram_gb = tco_config.get('required_ram_gb', 16) # Default 16GB
        ram_upgrade_flat_cost = tco_config.get('ram_upgrade_flat_cost', 30)   # Default $30 flat
        required_storage_gb = tco_config.get('required_storage_gb', 128) # Default 128GB
        storage_upgrade_flat_cost = tco_config.get('storage_upgrade_flat_cost', 15) # Default $15 flat

        # Log warnings if defaults are used for new TCO values
        if kwh_cost == 0.1 and 'kwh_cost' not in tco_config:
            logger.warning("kwh_cost not found in app.tco_assumptions, defaulting to 0.10.")
        if lifespan_years == tco_config.get('lifespan_years') and 'lifespan_years' not in tco_config: # Check against actual default if not in config
             logger.warning(f"lifespan_years not found in app.tco_assumptions, defaulting to {tco_config.get('lifespan_years', 5)}.")
        if shipping_t_cpu == 10 and 'shipping_cost_t_cpu' not in tco_config:
             logger.warning("shipping_cost_t_cpu not found in app.tco_assumptions, defaulting to $10.")
        if shipping_non_t_cpu == 35 and 'shipping_cost_non_t_cpu' not in tco_config:
             logger.warning("shipping_cost_non_t_cpu not found in app.tco_assumptions, defaulting to $35.")
        if required_ram_gb == 16 and 'required_ram_gb' not in tco_config: # Default 16GB
            logger.warning("required_ram_gb not found in app.tco_assumptions, defaulting to 16GB.")
        if ram_upgrade_flat_cost == 30 and 'ram_upgrade_flat_cost' not in tco_config:   # Default $30 flat
            logger.warning("ram_upgrade_flat_cost not found in app.tco_assumptions, defaulting to $30.")
        if required_storage_gb == 128 and 'required_storage_gb' not in tco_config: # Default 128GB
            logger.warning("required_storage_gb not found in app.tco_assumptions, defaulting to 128GB.")
        if storage_upgrade_flat_cost == 15 and 'storage_upgrade_flat_cost' not in tco_config: # Default $15 flat
            logger.warning("storage_upgrade_flat_cost not found in app.tco_assumptions, defaulting to $15.")

        for term in search_terms:
            logger.info(f"Searching for term: {term}")
            items, term_total = api.search_items(term, category_id, max_price, full_search=full_search)
            total_items_found_api += term_total 

            for item in items:
                item_id = item.get('itemId')
                if item_id in seen_item_ids:
                    logger.debug(f"Skipping duplicate item ID: {item_id}")
                    continue
                seen_item_ids.add(item_id)
                
                title = item.get('title', '').lower()
                cpu_model_str = '' 
                is_generic_intel_core_type = False
                generic_intel_core_type = None # Stores "I3", "I5", "I7" if model number is missing
                ram = ''
                storage = ''
            
                cpu_pattern = r'(?:(i[3579])(?:-([\d]{4,5}[a-z\d]*))?|(\bn\d{2,3}\b))'
                cpu_match = re.search(cpu_pattern, title)
                
                if cpu_match:
                    if cpu_match.group(1) and cpu_match.group(2): # e.g., i7-8700T
                        cpu_model_str = (cpu_match.group(1) + "-" + cpu_match.group(2)).upper()
                        generic_intel_core_type = cpu_match.group(1).upper()
                    elif cpu_match.group(1): # e.g., i7 (generic)
                        cpu_model_str = cpu_match.group(1).upper()
                        is_generic_intel_core_type = True
                        generic_intel_core_type = cpu_model_str
                    elif cpu_match.group(3): # e.g., N100
                        cpu_model_str = cpu_match.group(3).upper()
                
                storage_pattern = r'(\d+\.?\d*\s*(?:TB|GB))\s*(?:SSD|HDD|NVME|SSHD|STORAGE|DRIVE|EMMC)|(?:SSD|HDD|NVME|SSHD|STORAGE|DRIVE|EMMC)\s*(\d+\.?\d*\s*(?:TB|GB))'
                storage_match = re.search(storage_pattern, title, re.IGNORECASE)
                if storage_match:
                    storage = storage_match.group(1) if storage_match.group(1) else storage_match.group(2)
                    storage = storage.upper().replace(" ", "")

                ram_pattern = r'(\d+\s*GB)\s*RAM|RAM\s*(\d+\s*GB)|(\d+GB)\s*(?:DDR[345])'
                ram_match = re.search(ram_pattern, title, re.IGNORECASE)
                if ram_match:
                    ram = ram_match.group(1) or ram_match.group(2) or ram_match.group(3)
                    ram = ram.upper().replace(" ", "")

                if not cpu_model_str and not is_generic_intel_core_type:
                    if 'celeron' in title: cpu_model_str = 'CELERON'
                    elif 'pentium' in title: cpu_model_str = 'PENTIUM'
                    elif 'atom' in title: cpu_model_str = 'ATOM'
                    elif 'xeon' in title: cpu_model_str = 'XEON'
                    elif 'ryzen' in title: cpu_model_str = 'RYZEN'
                    elif 'athlon' in title: cpu_model_str = 'ATHLON'
                
                if not storage: storage = "N/A"
                if not ram: ram = "N/A"
                if not cpu_model_str and not is_generic_intel_core_type: cpu_model_str = "N/A"
                if is_generic_intel_core_type and not cpu_model_str: cpu_model_str = generic_intel_core_type # Ensure generic type is used if no specific model

                numeric_price = None
                price_str = item.get('price', {}).get('value')
                if price_str:
                    try:
                        numeric_price = float(price_str)
                    except ValueError:
                        logger.warning(f"Could not parse price for item {item_id}: {price_str}")

                performance_score = None
                if cpu_model_str != "N/A" and not is_generic_intel_core_type:
                    # Attempt 1: Direct lookup with the extracted model string (e.g., "I7-8700T", "N100")
                    performance_score = passmark_scores.get(cpu_model_str)

                    # Attempt 2: If Intel i-series and no score, try with "INTEL CORE " prefix
                    if not performance_score and generic_intel_core_type and cpu_model_str.startswith(generic_intel_core_type):
                        # This handles cases where cpu_model_str is "I7-8700T" and passmark key is "INTEL CORE I7-8700T"
                        # It also correctly handles if cpu_model_str is just "I7" (though this path is guarded by !is_generic_intel_core_type)
                        # but if it were, it would try "INTEL CORE I7"
                        potential_key = "INTEL CORE " + cpu_model_str
                        performance_score = passmark_scores.get(potential_key)
                    
                    # Attempt 3: For N-series, if no score, try common prefixes like "INTEL " or "INTEL CELERON "
                    if not performance_score and cpu_model_str.startswith('N'):
                        performance_score = passmark_scores.get("INTEL " + cpu_model_str)
                        if not performance_score:
                            performance_score = passmark_scores.get("INTEL CELERON " + cpu_model_str)

                    # Attempt 4: If still no score, use precise substring matching as a fallback
                    if not performance_score:
                        found_substring_match = False
                        for passmark_key, score_value in passmark_scores.items():
                            if is_precise_substring_match(cpu_model_str, passmark_key):
                                performance_score = score_value
                                found_substring_match = True
                                logger.debug(f"PassMark substring match: Extracted '{cpu_model_str}' in PassMark key '{passmark_key}' -> {score_value}")
                                break # Use the first precise substring match
                        
                        if not found_substring_match:
                            cpus_not_found_in_passmark.add(cpu_model_str)
                    # If performance_score is found by any method, it will be used.

                elif cpu_model_str in ('I3', 'I5', 'I7', 'I9') and cpu_model_str not in cpus_not_found_in_passmark: # Check generic types
                     logger.debug(f"PassMark lookup skipped for generic CPU type '{cpu_model_str}'.")
                     # Intentionally no cpus_not_found_in_passmark.add here for generics

                free_shipping = False
                shipping_options = item.get('shippingOptions', [])
                if shipping_options:
                    first_option = shipping_options[0]
                    is_explicitly_free = first_option.get('freeShipping', False) 
                    if isinstance(is_explicitly_free, str):
                        is_explicitly_free = is_explicitly_free.lower() == 'true'
                    if is_explicitly_free:
                        free_shipping = True
                    else:
                        shipping_cost_details = first_option.get('shippingCost', {})
                        if isinstance(shipping_cost_details, dict): # Ensure it's a dict
                            shipping_cost_value = shipping_cost_details.get('value')
                            if shipping_cost_value is not None:
                                try:
                                    if float(shipping_cost_value) == 0.0:
                                        free_shipping = True
                                except ValueError:
                                    logger.debug(f"Could not parse shipping cost value '{shipping_cost_value}' to float for item {item_id}")
                elif 'free shipping' in title or 'shipping included' in title:
                    free_shipping = True
                
                tco = None
                idle_watts = None
                
                if cpu_model_str != "N/A" and not is_generic_intel_core_type:
                    term1_raw_model = cpu_model_str.upper()
                    term2_prefixed_model = None

                    if generic_intel_core_type and not cpu_model_str.startswith(generic_intel_core_type): # e.g. cpu_model_str is "8700T", generic_intel_core_type is "I7"
                        term2_prefixed_model = f"{generic_intel_core_type}-{cpu_model_str}".upper()
                    elif generic_intel_core_type and cpu_model_str.startswith(generic_intel_core_type + "-"): # Already prefixed like I7-8700T
                         pass # term1_raw_model is already the prefixed version

                    idle_watts = idle_power_data.get(term1_raw_model)
                    if not idle_watts and term2_prefixed_model:
                        idle_watts = idle_power_data.get(term2_prefixed_model)

                    if not idle_watts: # Substring search as fallback
                        for key, val in idle_power_data.items():
                            if is_precise_substring_match(term1_raw_model, key):
                                idle_watts = val
                                logger.debug(f"Idle power substring match: '{term1_raw_model}' in '{key}' -> {val}W")
                                break
                            if term2_prefixed_model and is_precise_substring_match(term2_prefixed_model, key):
                                idle_watts = val
                                logger.debug(f"Idle power substring match (prefixed): '{term2_prefixed_model}' in '{key}' -> {val}W")
                                break
                        if not idle_watts:
                            cpus_not_found_in_idlepower.add(cpu_model_str)
                elif is_generic_intel_core_type:
                    logger.debug(f"Idle power lookup skipped for generic CPU type '{cpu_model_str}' for TCO.")


                if numeric_price is not None and idle_watts is not None:
                    energy_cost_calc = (idle_watts / 1000) * (24 * 365 * lifespan_years) * kwh_cost
                    shipping_cost_to_add = 0
                    if not free_shipping:
                        if cpu_model_str.endswith('T'): # Check original cpu_model_str for 'T'
                            shipping_cost_to_add = shipping_t_cpu
                        else:
                            shipping_cost_to_add = shipping_non_t_cpu
                    
                    ram_shortfall_cost = 0
                    item_ram_gb = parse_capacity_to_gb(ram)
                    if item_ram_gb < required_ram_gb:
                        ram_shortfall_cost = ram_upgrade_flat_cost

                    storage_shortfall_cost = 0
                    item_storage_gb = parse_capacity_to_gb(storage)
                    if item_storage_gb < required_storage_gb:
                        storage_shortfall_cost = storage_upgrade_flat_cost
                        
                    tco = numeric_price + energy_cost_calc + shipping_cost_to_add + ram_shortfall_cost + storage_shortfall_cost
                
                calculated_performance_per_dollar = None
                if performance_score and tco and tco > 0: # Use TCO for this calculation
                    calculated_performance_per_dollar = performance_score / tco

                all_results.append({
                    'title': item.get('title'),
                    'price': numeric_price,
                    'cpu_type': generic_intel_core_type if generic_intel_core_type else ('N-SERIES' if cpu_model_str.startswith('N') else ('AMD' if 'RYZEN' in cpu_model_str or 'ATHLON' in cpu_model_str else 'OTHER')),
                    'cpu_model': cpu_model_str if not is_generic_intel_core_type else generic_intel_core_type, # Display generic type if no specific model number
                    'ram': ram,
                    'storage': storage,
                    'performance': performance_score,
                    'free_shipping': free_shipping,
                    'tco': tco,
                    'performance_per_dollar': calculated_performance_per_dollar,
                    'item_url': item.get('itemWebUrl'),
                    'image_url': item.get('image', {}).get('imageUrl'),
                    'cpu_idle_power': idle_watts # Added for frontend TCO recalculation
                })

        # End of the for term in search_terms loop
        logger.info(f"Total items processed after API search and filtering: {len(all_results)}")
        logger.info(f"Total items found by API across all search terms: {total_items_found_api}")
        
        if cpus_not_found_in_passmark:
            logger.info(f"CPUs not found in PassMark (first occurrence): {', '.join(sorted(list(cpus_not_found_in_passmark)))}\n")
        if cpus_not_found_in_idlepower:
            logger.info(f"CPUs not found in Idle Power (first occurrence): {', '.join(sorted(list(cpus_not_found_in_idlepower)))}\n")
            
        tco_defaults_for_frontend = {
            'kwh_cost': kwh_cost,
            'lifespan_years': lifespan_years,
            'shipping_cost_t_cpu': shipping_t_cpu,
            'shipping_cost_non_t_cpu': shipping_non_t_cpu,
            'required_ram_gb': required_ram_gb,
            'ram_upgrade_flat_cost': ram_upgrade_flat_cost,
            'required_storage_gb': required_storage_gb,
            'storage_upgrade_flat_cost': storage_upgrade_flat_cost
        }
            
        return jsonify({
            'status': 'success', 
            'listings': all_results, 
            'total_found': total_items_found_api,
            'actually_processed': len(all_results),
            'full_search_enabled': full_search,
            'tco_defaults': tco_defaults_for_frontend
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        current_full_search_status = config.get('search', {}).get('full_search', False)
        return jsonify({'status': 'error', 'message': f'API request failed: {str(e)}', 'listings': [], 'total_found': 0, 'full_search_enabled': current_full_search_status}), 500
    except Exception as e:
        logger.error(f"Error in search route: {e}", exc_info=True)
        current_full_search_status = config.get('search', {}).get('full_search', False)
        return jsonify({'status': 'error', 'message': str(e), 'listings': [], 'total_found': 0, 'full_search_enabled': current_full_search_status}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 