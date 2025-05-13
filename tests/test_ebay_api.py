#!/usr/bin/env python3
"""
Test script for eBay API functionality.
"""
import os
import sys
import logging
import base64
import json
import yaml
from src.ebay_api import EBayAPI
import pytest
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from file."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        return None

def test_ebay_api(monkeypatch, mocker):
    """Test eBay API functionality with mocked external calls."""
    monkeypatch.setenv('EBAY_CLIENT_ID', 'test_client_id_api')
    monkeypatch.setenv('EBAY_CLIENT_SECRET', 'test_client_secret_api')
    app_id = os.getenv('EBAY_CLIENT_ID')
    cert_id = os.getenv('EBAY_CLIENT_SECRET')
    
    assert app_id and cert_id, "Missing eBay API credentials in environment variables"
    
    ebay_api = EBayAPI(
        app_id=app_id,
        cert_id=cert_id,
        sandbox=False 
    )
    logger.info("✅ EBayAPI initialized successfully!")

    # Mock requests.post for get_oauth_token
    mock_oauth_response = MagicMock()
    mock_oauth_response.json.return_value = {
        'access_token': 'fake_token',
        'expires_in': 7200
    }
    mock_oauth_response.raise_for_status = MagicMock() # Ensure it doesn't raise
    mocker.patch('requests.post', return_value=mock_oauth_response)
    
    logger.info("Getting OAuth token (mocked)...")
    assert ebay_api.get_oauth_token(), "Failed to get OAuth token (mocked)"
    assert ebay_api.token == 'fake_token'
    logger.info("✅ Successfully obtained access token (mocked)!")
    
    # Mock requests.get for search_items
    mock_search_response = MagicMock()
    dummy_item_summary = {
        'itemId': 'v1|12345|0',
        'title': 'Mocked Laptop 1',
        'price': {'value': '100.00', 'currency': 'USD'},
        'itemWebUrl': 'http://example.com/mockedlaptop1'
    }
    mock_search_response.json.return_value = {
        'itemSummaries': [dummy_item_summary],
        'total': 1,
        'next': None
    }
    mock_search_response.raise_for_status = MagicMock()
    
    # Mock requests.get for get_item_details
    mock_details_response = MagicMock()
    mock_details_response.json.return_value = {
        'itemId': 'v1|12345|0',
        'title': 'Mocked Laptop 1 Detailed',
        'price': {'value': '100.00', 'currency': 'USD'},
        'condition': 'New',
        'itemLocation': {'country': 'US'},
        'seller': {'username': 'test_seller_mocked'}
    }
    mock_details_response.raise_for_status = MagicMock()

    # We need to make sure requests.get is patched correctly for different URLs
    # A more robust way is to use a side_effect function for mocker.patch('requests.get')
    def mock_requests_get_side_effect(*args, **kwargs):
        if 'item_summary/search' in args[0]: # URL for search
            return mock_search_response
        elif f"/item/{dummy_item_summary['itemId']}" in args[0]: # URL for item details
            return mock_details_response
        raise ValueError(f"Unexpected GET request to {args[0]}")

    mocker.patch('requests.get', side_effect=mock_requests_get_side_effect)

    logger.info("Testing search functionality (mocked)...")
    results, total_found = ebay_api.search_items(keywords="laptop")
    assert len(results) == 1
    assert total_found == 1
    assert results[0]['title'] == 'Mocked Laptop 1'
    logger.info(f"✅ Search completed successfully (mocked)! Found {len(results)} items, API reported {total_found}")
    
    if results:
        first_item = results[0]
        item_id = first_item.get('itemId')
        assert item_id, "First item has no itemId to look up (mocked)"
        logger.info("\nTesting item lookup (mocked)...")
        item_details = ebay_api.get_item_details(item_id)
        assert item_details, f"Failed to get item details for {item_id} (mocked)"
        assert item_details['title'] == 'Mocked Laptop 1 Detailed'
        logger.info("✅ Item lookup completed successfully (mocked)!")
        # ... (log more details if needed)

if __name__ == "__main__":
    logger.info("Starting eBay API test with mocks")
    pytest.main([__file__]) # Run this specific test file

    # if success:
    #     logger.info("✅ All tests completed successfully!")
    #     sys.exit(0)
    # else:
    #     logger.error("❌ Tests failed")
    #     sys.exit(1) 