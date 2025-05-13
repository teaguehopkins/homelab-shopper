"""
Total Cost of Ownership (TCO) calculation module for the Homelab Deal Finder.
Handles calculations for power consumption, missing parts, and performance ratios.
"""
import logging
from typing import Dict, Optional, List, Union, Tuple

# Configure logging
logger = logging.getLogger(__name__)

def calculate_power_cost(idle_watts: float, electricity_cost_per_kwh: float, 
                        lifespan_years: int) -> float:
    """
    Calculate the total electricity cost over the lifespan.
    
    Args:
        idle_watts: Power consumption in watts at idle
        electricity_cost_per_kwh: Cost per kilowatt-hour in dollars
        lifespan_years: Expected lifespan in years
        
    Returns:
        Total electricity cost over the lifespan in dollars
    """
    hours_per_year = 24 * 365.25  # Account for leap years
    total_hours = hours_per_year * lifespan_years
    kilowatts = idle_watts / 1000
    total_kwh = kilowatts * total_hours
    
    return total_kwh * electricity_cost_per_kwh

def estimate_missing_parts_cost(parsed_specs: Dict[str, Optional[str]], 
                              reference_costs: Dict[str, float]) -> Tuple[float, List[str]]:
    """
    Calculate the cost of missing parts based on parsed specifications.
    
    Args:
        parsed_specs: Dictionary containing parsed specifications (RAM, storage)
        reference_costs: Dictionary containing reference costs for parts
        
    Returns:
        Tuple of (total cost of missing parts, list of missing parts)
    """
    total_cost = 0.0
    missing_parts = []
    
    # Check RAM
    if not parsed_specs.get('ram'):
        ram_cost = reference_costs.get('ram_8gb_ddr4', 0)
        total_cost += ram_cost
        missing_parts.append('8GB DDR4 RAM')
    
    # Check storage
    if not parsed_specs.get('storage'):
        storage_cost = reference_costs.get('ssd_256gb_sata', 0)
        total_cost += storage_cost
        missing_parts.append('256GB SATA SSD')
    
    return total_cost, missing_parts

def calculate_tco(listing_price: float, parsed_specs: Dict[str, Optional[str]], 
                 cpu_specs: Optional[Dict[str, float]], config: Dict) -> Optional[Dict[str, Union[float, List[str]]]]:
    """
    Calculate the Total Cost of Ownership for a listing.
    
    Args:
        listing_price: Current price of the listing
        parsed_specs: Dictionary containing parsed specifications
        cpu_specs: Dictionary containing CPU specifications (passmark, idle_watts)
        config: Configuration dictionary containing reference data and parameters
        
    Returns:
        Dictionary containing TCO breakdown or None if calculation not possible
    """
    try:
        if not cpu_specs:
            logger.warning("Cannot calculate TCO without CPU specifications")
            return None
            
        # Get configuration parameters
        lifespan_years = config['tco_lifespan_years']
        electricity_cost = config['electricity_cost_per_kwh']
        reference_costs = config['missing_parts_costs']
        
        # Calculate power cost
        power_cost = calculate_power_cost(
            cpu_specs['idle_watts'],
            electricity_cost,
            lifespan_years
        )
        
        # Calculate missing parts cost
        parts_cost, missing_parts = estimate_missing_parts_cost(parsed_specs, reference_costs)
        
        # Calculate total TCO
        total_tco = listing_price + power_cost + parts_cost
        
        return {
            'total_tco': total_tco,
            'breakdown': {
                'listing_price': listing_price,
                'power_cost': power_cost,
                'missing_parts_cost': parts_cost
            },
            'missing_parts': missing_parts,
            'assumptions': {
                'lifespan_years': lifespan_years,
                'electricity_cost_per_kwh': electricity_cost,
                'idle_watts': cpu_specs['idle_watts']
            }
        }
        
    except (KeyError, TypeError) as e:
        logger.error(f"Error calculating TCO: {str(e)}")
        return None

def calculate_performance_ratio(cpu_specs: Optional[Dict[str, float]], 
                             tco_result: Optional[Dict[str, Union[float, List[str]]]]) -> Optional[float]:
    """
    Calculate the performance-to-TCO ratio.
    
    Args:
        cpu_specs: Dictionary containing CPU specifications
        tco_result: Dictionary containing TCO calculation results
        
    Returns:
        Performance per dollar ratio or None if calculation not possible
    """
    try:
        if not cpu_specs or not tco_result:
            logger.warning("Cannot calculate performance ratio without CPU specs and TCO")
            return None
            
        total_tco = tco_result['total_tco']
        if total_tco <= 0:
            logger.warning("Invalid TCO value (zero or negative)")
            return None
            
        return cpu_specs['passmark'] / total_tco
        
    except (KeyError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Error calculating performance ratio: {str(e)}")
        return None 