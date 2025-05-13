"""
Tests for the TCO calculation module.
"""
import pytest
from src.tco import (
    calculate_power_cost,
    estimate_missing_parts_cost,
    calculate_tco,
    calculate_performance_ratio
)

@pytest.fixture
def sample_config():
    """Sample configuration data."""
    return {
        'tco_lifespan_years': 5,
        'electricity_cost_per_kwh': 0.14,
        'missing_parts_costs': {
            'ram_8gb_ddr4': 25,
            'ssd_256gb_sata': 30
        }
    }

@pytest.fixture
def sample_cpu_specs():
    """Sample CPU specifications."""
    return {
        'passmark': 5000,
        'idle_watts': 15
    }

def test_calculate_power_cost():
    """Test power cost calculation."""
    # Test with sample values
    cost = calculate_power_cost(
        idle_watts=15,
        electricity_cost_per_kwh=0.14,
        lifespan_years=5
    )
    
    # 15W = 0.015kW
    # Hours in 5 years = 24 * 365.25 * 5 = 43,830
    # Total kWh = 0.015 * 43,830 = 657.45
    # Cost = 657.45 * 0.14 = 92.043
    assert round(cost, 2) == 92.04
    
    # Test with zero watts
    assert calculate_power_cost(0, 0.14, 5) == 0
    
    # Test with zero cost
    assert calculate_power_cost(15, 0, 5) == 0

def test_estimate_missing_parts_cost():
    """Test missing parts cost estimation."""
    reference_costs = {
        'ram_8gb_ddr4': 25,
        'ssd_256gb_sata': 30
    }
    
    # Test with all parts missing
    cost, parts = estimate_missing_parts_cost(
        parsed_specs={'ram': None, 'storage': None},
        reference_costs=reference_costs
    )
    assert cost == 55  # 25 + 30
    assert len(parts) == 2
    assert '8GB DDR4 RAM' in parts
    assert '256GB SATA SSD' in parts
    
    # Test with RAM present
    cost, parts = estimate_missing_parts_cost(
        parsed_specs={'ram': '16GB', 'storage': None},
        reference_costs=reference_costs
    )
    assert cost == 30
    assert len(parts) == 1
    assert '256GB SATA SSD' in parts
    
    # Test with all parts present
    cost, parts = estimate_missing_parts_cost(
        parsed_specs={'ram': '16GB', 'storage': '512GB'},
        reference_costs=reference_costs
    )
    assert cost == 0
    assert len(parts) == 0

def test_calculate_tco(sample_config, sample_cpu_specs):
    """Test TCO calculation."""
    # Test with all parts missing
    result = calculate_tco(
        listing_price=200,
        parsed_specs={'ram': None, 'storage': None},
        cpu_specs=sample_cpu_specs,
        config=sample_config
    )
    
    assert result is not None
    assert 'total_tco' in result
    assert 'breakdown' in result
    assert 'missing_parts' in result
    assert 'assumptions' in result
    
    # Verify breakdown
    breakdown = result['breakdown']
    assert breakdown['listing_price'] == 200
    assert round(breakdown['power_cost'], 2) == 92.04
    assert breakdown['missing_parts_cost'] == 55
    
    # Verify total
    expected_total = 200 + 92.04 + 55
    assert round(result['total_tco'], 2) == round(expected_total, 2)
    
    # Test with invalid CPU specs
    result = calculate_tco(
        listing_price=200,
        parsed_specs={'ram': None, 'storage': None},
        cpu_specs=None,
        config=sample_config
    )
    assert result is None
    
    # Test with missing config keys
    result = calculate_tco(
        listing_price=200,
        parsed_specs={'ram': None, 'storage': None},
        cpu_specs=sample_cpu_specs,
        config={}
    )
    assert result is None

def test_calculate_performance_ratio(sample_cpu_specs):
    """Test performance ratio calculation."""
    # Test with valid inputs
    tco_result = {
        'total_tco': 347.04,  # From previous test
        'breakdown': {}  # Not needed for this test
    }
    
    ratio = calculate_performance_ratio(sample_cpu_specs, tco_result)
    assert ratio is not None
    # Expected ratio = 5000 / 347.04 ≈ 14.41
    assert round(ratio, 2) == 14.41
    
    # Test with missing CPU specs
    ratio = calculate_performance_ratio(None, tco_result)
    assert ratio is None
    
    # Test with missing TCO result
    ratio = calculate_performance_ratio(sample_cpu_specs, None)
    assert ratio is None
    
    # Test with zero TCO
    ratio = calculate_performance_ratio(sample_cpu_specs, {'total_tco': 0})
    assert ratio is None 