"""
eBay API integration module for the Homelab Deal Finder.
"""
import logging
import base64
import requests
import json
import os
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urlencode, quote_plus, parse_qs, urlparse
from pathlib import Path  # NEW: path handling
import tempfile  # NEW: fallback directory for token storage
# --- Optional encryption support --------------------------------------
# Cryptography is listed in requirements, but to avoid import-time
# failures (e.g. when the library or its type stubs are missing in an
# editor environment) we wrap it in a try/except and degrade gracefully.
try:
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
except ImportError:  # pragma: no cover – treat encryption as optional
    Fernet = None  # type: ignore[assignment]
    class _Dummy(Exception):
        """Placeholder to keep type checkers happy when cryptography absent."""
    InvalidToken = _Dummy  # type: ignore[valid-type]

# Configure logging
logger = logging.getLogger(__name__)

class EBayAPI:
    """Class to handle eBay API interactions."""
    
    def __init__(self, app_id, cert_id, sandbox=True, token_file: str | None = None):
        """Initialize the eBay API client with credentials.

        Args:
            app_id: eBay App-ID.
            cert_id: eBay Cert-ID.
            sandbox: Use the eBay sandbox endpoint when True.
            token_file: Optional path where the OAuth bearer token will be
                cached.  If ``None`` the path is resolved in this order:

                1. ``$EBAY_TOKEN_PATH`` environment variable (absolute or
                   relative).
                2. ``<tmpdir>/ebay_token.json`` where *tmpdir* is the OS
                   temporary directory.  The location is outside the project
                   repo, preventing accidental check-in.
        """
        if not app_id or not cert_id:
            raise ValueError("eBay API credentials are required")
            
        self.app_id = app_id
        self.cert_id = cert_id
        self.sandbox = sandbox
        self.base_url = (
            "https://api.sandbox.ebay.com/buy/browse/v1"
            if sandbox
            else "https://api.ebay.com/buy/browse/v1"
        )

        # ---------------- Encryption key -------------------------------
        enc_key = os.getenv("EBAY_TOKEN_ENC_KEY")
        self._fernet: object | None = None
        if enc_key:
            try:
                # Key must be URL-safe base64 32-byte key (44 chars)
                self._fernet = Fernet(enc_key.encode())
            except Exception as exc:  # pragma: no cover – invalid key
                logger.error("Invalid EBAY_TOKEN_ENC_KEY: %s", exc)
                self._fernet = None

        # ---------------- Token file path resolution -------------------
        if token_file is None:
            token_file = os.getenv("EBAY_TOKEN_PATH")

        if not token_file:
            # Fall back to a safe location outside the repo tree
            token_file = str(Path(tempfile.gettempdir()) / "ebay_token.json")

        self.token_file: Path = Path(token_file)
        self.token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Load existing token if available
        self._load_token()
        
        # Initialize headers
        self.headers = {
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }
        
        # Update headers with token if available
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
            logger.info(f"Initialized eBay API with {'sandbox' if sandbox else 'production'} URL: {self.base_url}")
        else:
            logger.info("No valid token found. Please authenticate first.")
    
    def _load_token(self):
        """Load token from file if it exists and is not expired."""
        if self.token_file.exists():
            try:
                # Read raw bytes; may be encrypted
                raw_bytes = self.token_file.read_bytes()

                if self._fernet is not None:
                    try:
                        raw_bytes = self._fernet.decrypt(raw_bytes)
                    except InvalidToken:
                        logger.error("Failed to decrypt token file. Wrong key?")
                        return

                try:
                    token_data = json.loads(raw_bytes.decode())
                except Exception as json_exc:
                    logger.error("Token file is corrupt or not JSON: %s", json_exc)
                    return
                    
                # Check if token is expired
                expiry = datetime.fromisoformat(token_data['expiry'])
                if expiry > datetime.now():
                    self.token = token_data['access_token']
                    self.refresh_token = token_data.get('refresh_token')
                    self.token_expiry = expiry
                    logger.info("Loaded valid token from file")
                else:
                    logger.info("Token expired, will need to refresh")
            except Exception as e:
                logger.error(f"Error loading token: {str(e)}")
    
    def _save_token(self, token_data):
        """Save token data to file."""
        try:
            # Ensure parent directory exists (e.g. /run/secrets)
            self.token_file.parent.mkdir(parents=True, exist_ok=True)

            data_bytes = json.dumps(token_data).encode()
            if self._fernet is not None:
                data_bytes = self._fernet.encrypt(data_bytes)

            with self.token_file.open('wb') as f:
                f.write(data_bytes)

            try:
                self.token_file.chmod(0o600)
            except Exception as perm_exc:  # pragma: no cover – best-effort
                logger.debug("Could not set permissions on token file: %s", perm_exc)

            logger.info("Token saved to %s", self.token_file)
        except Exception as e:
            logger.error(f"Error saving token: {str(e)}")
    
    def get_oauth_token(self):
        """Get OAuth token using client-credentials flow.

        If a non-expired token is already loaded in ``self.token`` we simply
        return ``True`` without hitting the eBay identity endpoint again.
        """
        # Short-circuit when we already have a token that is valid for at
        # least another minute. This avoids an extra network round-trip on
        # every request/cron run.
        if self.token and self.token_expiry and (self.token_expiry - datetime.now()).total_seconds() > 60:
            return True  # Token still good – nothing to do.

        token_url = (
            "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
            if self.sandbox
            else "https://api.ebay.com/identity/v1/oauth2/token"
        )

        # Create Base64 encoded credentials
        credentials = f"{self.app_id}:{self.cert_id}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.token = token_data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=token_data.get("expires_in", 7200))

            # Save token data
            self._save_token({
                "access_token": self.token,
                "expiry": self.token_expiry.isoformat(),
            })

            # Update headers
            self.headers["Authorization"] = f"Bearer {self.token}"

            logger.info("Successfully obtained access token")
            return True

        except requests.exceptions.RequestException as e:  # pragma: no cover – network errors
            logger.error("Error getting OAuth token: %s", e)
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response text: %s", e.response.text)
            return False
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token."""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
            
        token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token" if self.sandbox else "https://api.ebay.com/identity/v1/oauth2/token"
        
        # Create Base64 encoded credentials
        credentials = f"{self.app_id}:{self.cert_id}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_data.get('expires_in', 7200))
            
            # Save token data
            self._save_token({
                'access_token': self.token,
                'refresh_token': self.refresh_token,  # Keep the same refresh token
                'expiry': self.token_expiry.isoformat()
            })
            
            # Update headers
            self.headers["Authorization"] = f"Bearer {self.token}"
            
            logger.info("Successfully refreshed access token")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response text: {e.response.text}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def search_items(self, keywords: str, category_id: int = None, max_price: float = None, full_search: bool = False) -> tuple:
        """
        Search for items on eBay matching the given criteria, with optional pagination.
        
        Args:
            keywords: Single search keyword string.
            category_id: eBay category ID (optional).
            max_price: Maximum item price (optional) - Used for API filtering.
            full_search: If True, attempt to paginate through all result pages.
            
        Returns:
            A tuple containing: (list of all found item summaries, total items found by API).
            Returns ([], 0) on failure.
        """
        if not self.token:
            logger.error("Authentication token is not available")
            return [], 0
            
        search_url = f"{self.base_url}/item_summary/search"
        
        params = {
            "q": keywords,
            "limit": 200, # Request max limit per page
            "offset": 0
        }
        
        filters = []
        if category_id:
            params["category_ids"] = str(category_id)
        if max_price:
            filters.append(f"price:[..{max_price}],priceCurrency:USD")
            
        # Add other filters like condition, buying options if needed later
        # Example: filters.append("buyingOptions:{AUCTION|FIXED_PRICE}")
        # filters.append("conditionIds:{1000|1500|2000|...}")
        
        if filters:
            params["filter"] = ",".join(filters)
            
        all_items = []
        total_from_api = 0
        current_page = 1
        max_pages_to_fetch = 50 # Safety limit: Fetch max 50 pages (e.g., 50 * 200 = 10,000 items)

        while True:
            logger.info(f"Fetching page {current_page} (offset {params['offset']}) for keywords: '{keywords}'")
            try:
                response = requests.get(search_url, headers=self.headers, params=params)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()
                
                # Get total count from the first page
                if params['offset'] == 0:
                    total_from_api = data.get("total", 0)
                    logger.info(f"API reported total of {total_from_api} items for '{keywords}'")
                    if total_from_api == 0:
                        break # No items found at all
                        
                items_on_page = data.get("itemSummaries", [])
                if not items_on_page:
                    logger.info("No more items found on this page.")
                    break # No more items returned
                    
                all_items.extend(items_on_page)
                logger.info(f"Fetched {len(items_on_page)} items. Total accumulated: {len(all_items)}")

                # Check if we should continue pagination
                if not full_search or current_page >= max_pages_to_fetch:
                    logger.info(f"Stopping search for '{keywords}'. full_search={full_search}, page={current_page}, max_pages={max_pages_to_fetch}")
                    break 

                # --- Get next offset --- 
                next_url_str = data.get("next")
                if next_url_str:
                    try:
                        # Parse the next URL to reliably get the offset
                        parsed_url = urlparse(next_url_str)
                        query_params = parse_qs(parsed_url.query)
                        next_offset = int(query_params.get('offset', [None])[0])
                        if next_offset is not None and next_offset > params['offset']:
                            params['offset'] = next_offset
                            current_page += 1
                        else:
                            logger.warning("Could not parse valid next offset or offset did not increase. Stopping pagination.")
                            break
                    except Exception as parse_err:
                        logger.warning(f"Error parsing next URL '{next_url_str}': {parse_err}. Stopping pagination.")
                        break
                else:
                    logger.info("No 'next' URL provided by API. Reached end of results.")
                    break # No more pages indicated by API

            except requests.exceptions.HTTPError as http_err:
                logger.error(f"HTTP error during search for '{keywords}' (page {current_page}): {http_err}")
                logger.error(f"Response Status: {http_err.response.status_code}, Response Text: {http_err.response.text}")
                # Depending on the error, we might want to break or let tenacity handle retries
                if http_err.response.status_code in [401, 403]: # Authentication errors - stop
                     logger.error("Authentication error. Cannot continue search.")
                     # Potentially try token refresh here if applicable and configured
                     return [], 0 # Return failure
                # For other errors (like 400, 500), let tenacity handle retries based on the decorator
                # If retries fail, the exception will propagate up.
                raise # Re-raise to trigger tenacity retry
            except Exception as e:
                logger.error(f"Error during search for '{keywords}' (page {current_page}): {str(e)}", exc_info=True)
                return [], 0 # Return failure on unexpected errors

        logger.info(f"Search complete for '{keywords}'. Total items retrieved: {len(all_items)}. API reported total: {total_from_api}.")
        return all_items, total_from_api
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_item_details(self, item_id: str) -> dict:
        """
        Get detailed information about a specific item.
        
        Args:
            item_id: eBay item ID
            
        Returns:
            Dictionary containing detailed item information
        """
        try:
            response = requests.get(
                f"{self.base_url}/item/{item_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting item details: {str(e)}")
            raise
    
    def get_item_specifications(self, item_id: str) -> dict:
        """
        Get technical specifications for an item.
        
        Args:
            item_id: eBay item ID
            
        Returns:
            Dictionary containing item specifications
        """
        try:
            response = requests.get(
                f"{self.base_url}/item/{item_id}/get_item_aspects",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting item specifications: {str(e)}")
            raise 