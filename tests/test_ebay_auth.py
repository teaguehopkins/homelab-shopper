#!/usr/bin/env python3
"""
Test script for eBay API authentication and functionality.
"""
import os
import sys
import logging
from src.ebay_api import EBayAPI
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ebay_api(monkeypatch):
    """Test eBay API authentication and basic search."""
    # Get credentials from environment variables
    monkeypatch.setenv('EBAY_CLIENT_ID', 'test_client_id_auth')
    monkeypatch.setenv('EBAY_CLIENT_SECRET', 'test_client_secret_auth')
    app_id = os.getenv('EBAY_CLIENT_ID')
    cert_id = os.getenv('EBAY_CLIENT_SECRET')
    
    assert app_id and cert_id, "Missing eBay API credentials in environment variables"
        
    # Initialize API
    logger.info("Initializing EBayAPI...")
    ebay_api = EBayAPI(
        app_id=app_id,
        cert_id=cert_id,
        sandbox=True
    )
    
    # If we already have a valid token, we can skip authentication
    if ebay_api.token:
        logger.info("Using existing valid token")
    else:
        # Get application OAuth token
        logger.info("Attempting to get application OAuth token...")
        assert ebay_api.get_oauth_token(), "Failed to obtain application access token"
        logger.info("Successfully obtained application access token")
            
    # Test search
    logger.info("Testing search functionality...")
    results, total_found = ebay_api.search_items(keywords="laptop")
    logger.info(f"✅ Search completed successfully! Found {len(results)} items, API reported {total_found}")
    
    if results:
        # Print first result
        first_item = results[0]
        logger.info("\nFirst item details:")
        logger.info(f"Title: {first_item.get('title', 'N/A')}")
        logger.info(f"Price: {first_item.get('price', {}).get('value', 'N/A')} {first_item.get('price', {}).get('currency', 'N/A')}")
        logger.info(f"Item ID: {first_item.get('itemId', 'N/A')}")
        logger.info(f"Item Web URL: {first_item.get('itemWebUrl', 'N/A')}")
        
if __name__ == "__main__":
    logger.info("Starting eBay API (auth) test")
    pytest.main()
    
    # if success:
    #     logger.info("✅ All tests completed successfully!")
    #     sys.exit(0)
    # else:
    #     logger.error("❌ Tests failed")
    #     sys.exit(1) 