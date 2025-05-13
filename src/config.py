import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load and validate a YAML configuration file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Dictionary containing the configuration
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the file is not valid YAML
        ValueError: If required keys are missing
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

def validate_config(config: Dict[str, Any]) -> None:
    """Validate the main configuration file structure.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If required keys are missing
    """
    required_keys = ['tco_lifespan_years', 'electricity_cost_per_kwh', 
                    'missing_parts_costs', 'cpu_reference_data']
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    
    # Validate CPU reference data structure
    for cpu_model, specs in config['cpu_reference_data'].items():
        if not isinstance(specs, dict):
            raise ValueError(f"Invalid CPU specs format for {cpu_model}")
        if 'passmark' not in specs or 'idle_watts' not in specs:
            raise ValueError(f"Missing required CPU specs for {cpu_model}")

def validate_searches(searches: Dict[str, Any]) -> None:
    """Validate the searches configuration structure.
    
    Args:
        searches: Searches configuration dictionary to validate
        
    Raises:
        ValueError: If required keys are missing
    """
    if 'searches' not in searches:
        raise ValueError("Missing 'searches' key in searches configuration")
    
    for search in searches['searches']:
        required_keys = ['name', 'keywords', 'category_id']
        for key in required_keys:
            if key not in search:
                raise ValueError(f"Missing required search key: {key}")

def load_config(config_file: str = 'config.yaml') -> Dict[str, Any]:
    """Load application configuration from YAML file."""
    try:
        # Load from config.yaml file
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        
        # Replace environment variables in the config
        _replace_env_vars(config)
        
        # Validate eBay credentials
        _validate_ebay_credentials(config)
        
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise

def _replace_env_vars(config):
    """Replace environment variable placeholders in config."""
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, (dict, list)):
                _replace_env_vars(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                env_value = os.getenv(env_var)
                if env_value:
                    config[key] = env_value
                else:
                    logger.warning(f"Environment variable {env_var} not found")
    elif isinstance(config, list):
        for i, item in enumerate(config):
            if isinstance(item, (dict, list)):
                _replace_env_vars(item)
            elif isinstance(item, str) and item.startswith('${') and item.endswith('}'):
                env_var = item[2:-1]
                env_value = os.getenv(env_var)
                if env_value:
                    config[i] = env_value
                else:
                    logger.warning(f"Environment variable {env_var} not found")

def _validate_ebay_credentials(config):
    """Validate that eBay credentials are present and in the correct format."""
    try:
        app_id = config.get('ebay', {}).get('app_id')
        cert_id = config.get('ebay', {}).get('cert_id')
        
        if not app_id or app_id.startswith('${'):
            logger.error("Missing eBay App ID in configuration")
            raise ValueError("eBay App ID is required")
            
        if not cert_id or cert_id.startswith('${'):
            logger.error("Missing eBay Cert ID in configuration")
            raise ValueError("eBay Cert ID is required")
            
        logger.debug(f"Validated eBay credentials: AppID={app_id[:4]}..., CertID={cert_id[:4]}...")
    except Exception as e:
        logger.error(f"Error validating eBay credentials: {str(e)}")
        raise

# def get_api_credentials() -> Dict[str, str]:
#     """Get eBay API credentials from environment variables.
#     
#     Returns:
#         Dictionary containing API credentials
#         
#     Raises:
#         ValueError: If required credentials are missing
#     """
#     credentials = {
#         'api_key': os.getenv('EBAY_API_KEY'),
#         'client_id': os.getenv('EBAY_CLIENT_ID'),
#         'client_secret': os.getenv('EBAY_CLIENT_SECRET')
#     }
#     
#     # Check if we have at least one authentication method
#     if not any(credentials.values()):
#         raise ValueError("No eBay API credentials found in environment variables")
#     
#     return credentials 