"""
Tests for the database module.
"""
import pytest
from flask import Flask
from src.database import db as sqlalchemy_db, init_app, Listing # Updated import
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

@pytest.fixture(scope='session')
def app():
    """Create a Flask app instance for testing."""
    flask_app = Flask(__name__)
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['TESTING'] = True
    
    # Initialize SQLAlchemy with the app
    init_app(flask_app) # Use the init_app from src.database
    
    return flask_app

@pytest.fixture
def db(app):
    """Provides the database instance and handles setup/teardown."""
    with app.app_context():
        sqlalchemy_db.create_all() # Create tables
        
        yield sqlalchemy_db # This is what tests will use
        
        sqlalchemy_db.session.remove()
        sqlalchemy_db.drop_all()

@pytest.fixture
def sample_listing_data():
    """Sample listing data for testing."""
    return {
        'item_id': '123456',
        'title': 'Test Server',
        'price': 200.00,
        'url': 'http://example.com/item/123456',
        # 'seller': 'test_seller', # Seller not in current Listing model
        'cpu_model': 'Xeon E5-2670',
        'ram': '16GB',
        'storage': '256GB SSD',
        'tco': 347.04,
        # 'tco_breakdown': {}, # Not in current Listing model
        # 'performance_ratio': 14.41 # Not in current Listing model
    }

def test_add_listing(db, app, sample_listing_data): # Added app fixture
    """Test adding a new listing."""
    with app.app_context(): # Ensure operations are within app context
        from src.database import add_or_update_listing, Listing # Import here or make it available differently
        
        # Add listing using the function from src.database
        assert add_or_update_listing(**sample_listing_data)
        
        # Verify listing was added
        listing = db.session.get(Listing, '123456')
        assert listing is not None
        assert listing.title == 'Test Server'
        assert listing.price == 200.00
        assert listing.cpu_model == 'Xeon E5-2670'
        
        # Price history tests removed as the model is gone

def test_update_listing(db, app, sample_listing_data):
    """Test updating an existing listing."""
    with app.app_context():
        from src.database import add_or_update_listing, Listing

        # Add initial listing
        assert add_or_update_listing(**sample_listing_data)
        
        # Update listing
        updated_data = sample_listing_data.copy()
        updated_data['price'] = 180.00
        assert add_or_update_listing(**updated_data)
        
        # Verify update
        listing = db.session.get(Listing, '123456')
        assert listing is not None
        assert listing.price == 180.00
        
        # Price history tests removed

def test_get_all_listings(db, app, sample_listing_data):
    """Test retrieving all listings."""
    with app.app_context():
        from src.database import add_or_update_listing, get_all_listings

        # Add multiple listings
        listing1_data = sample_listing_data.copy()
        listing2_data = sample_listing_data.copy()
        listing2_data['item_id'] = '789012'
        listing2_data['title'] = 'Another Server'
        
        assert add_or_update_listing(**listing1_data)
        assert add_or_update_listing(**listing2_data)
        
        # Get all listings
        listings = get_all_listings()
        assert len(listings) == 2
        assert any(l.title == 'Test Server' for l in listings)
        assert any(l.title == 'Another Server' for l in listings)

def test_error_handling(db, app, sample_listing_data): # sample_listing_data might not be needed if we adapt the test
    """Test error handling for add_or_update_listing."""
    with app.app_context():
        from src.database import add_or_update_listing
        # Test invalid listing data (e.g., missing required fields for the function)
        # The add_or_update_listing function itself has default for optional fields.
        # A true error case would be if db.session.commit() fails.
        # For now, let's test with missing item_id which should be handled by SQLAlchemy or our function.
        invalid_data = sample_listing_data.copy()
        del invalid_data['item_id'] 
        # Depending on how add_or_update_listing handles missing item_id (it's a required arg)
        # this might raise TypeError before DB interaction.
        # If add_or_update_listing is robust to it and returns False:
        # assert not add_or_update_listing(**invalid_data) # This would fail if it raises TypeError

        # A more direct test for add_or_update_listing returning False due to commit error is hard to simulate
        # without deeper mocking of db.session.commit.
        # Let's test if trying to add with a non-string item_id (if that's a constraint not caught by Python types)
        # or a very long one if there's a length limit.
        
        # The original test's intent for 'invalid_data' (missing fields for model) is now
        # different because add_or_update_listing takes individual args.
        # A core requirement for add_or_update_listing is item_id, title, price, url.
        
        # Test case: Missing essential arguments for add_or_update_listing
        with pytest.raises(TypeError): # Assuming it will raise TypeError if item_id is missing
            add_or_update_listing(title="title only", price=10.0, url="url only")

        # Test non-existent listing for get_listing (adapted from original price history test)
        non_existent_listing = db.session.get(Listing, '999999')
        assert non_existent_listing is None

# Keep other imports if used by remaining tests, e.g. datetime, SQLAlchemyError
from datetime import datetime # Already imported at top
# from sqlalchemy.exc import SQLAlchemyError # If we add tests that expect this 