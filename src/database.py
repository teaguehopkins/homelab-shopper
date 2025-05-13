"""
Database module for the Homelab Deal Finder.
Handles database models and operations.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
import os
import logging

logger = logging.getLogger(__name__)

db = SQLAlchemy()

def init_app(app):
    """Initialize the database with the Flask app."""
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    # Only attempt to create directories if not using in-memory SQLite
    if not db_uri == 'sqlite:///:memory:' and db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '') # Get the file path part
        if db_path: # Ensure it's not just sqlite://
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir): # Check if db_dir is not empty (e.g. for relative paths)
                try:
                    os.makedirs(db_dir, mode=0o755, exist_ok=True)
                except OSError as e:
                    # This might happen if db_dir is, for example, '' for a relative path in current dir
                    # or if there's a genuine permission issue not caught by pre-checks.
                    logger.warning(f"Could not create database directory {db_dir}: {e}")
    
    # app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}' # This line is problematic if db_path is not defined for in-memory
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {str(e)}")
            raise
    
    return app

class Listing(db.Model):
    """Model for storing eBay listings."""
    __tablename__ = 'listings'
    
    # Primary key
    item_id = db.Column(db.String, primary_key=True)
    
    # Basic listing info
    title = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    url = db.Column(db.String, nullable=False)
    
    # Specifications
    cpu_model = db.Column(db.String)
    ram = db.Column(db.String)
    storage = db.Column(db.String)
    
    # TCO data
    tco = db.Column(db.Float)
    
    # Status tracking
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

def get_all_listings():
    """Get all listings from the database."""
    return Listing.query.all()

def add_or_update_listing(item_id, title, price, url, cpu_model=None, ram=None, storage=None, tco=None):
    """
    Add or update a listing in the database.
    
    Args:
        item_id: eBay item ID
        title: Listing title
        price: Current price
        url: eBay URL
        cpu_model: CPU model (optional)
        ram: RAM specification (optional)
        storage: Storage specification (optional)
        tco: Total Cost of Ownership (optional)
    """
    try:
        # Check if listing exists
        listing = db.session.get(Listing, item_id)
        
        if listing:
            # Update existing listing
            listing.title = title
            listing.price = price
            listing.url = url
            listing.cpu_model = cpu_model
            listing.ram = ram
            listing.storage = storage
            listing.tco = tco
            listing.last_updated = datetime.now(timezone.utc)
        else:
            # Create new listing
            listing = Listing(
                item_id=item_id,
                title=title,
                price=price,
                url=url,
                cpu_model=cpu_model,
                ram=ram,
                storage=storage,
                tco=tco
            )
            db.session.add(listing)
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        return False 