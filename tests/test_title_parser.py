import pytest
from src.title_parser import parse_title

@pytest.mark.parametrize(
    "title,expected",
    [
        (
            "Lenovo Tiny PC i7-8700T 16GB RAM 256GB SSD",
            {
                'cpu_model': 'I7-8700T',
                'generic_intel_core_type': 'I7',
                'is_generic_intel_core_type': False,
                'ram': '16GB',
                'storage': '256GB',
            },
        ),
        (
            "Dell OptiPlex Micro i5 8GB 1TB HDD",
            {
                'cpu_model': 'I5',
                'generic_intel_core_type': 'I5',
                'is_generic_intel_core_type': True,
                'ram': '8GB',
                'storage': '1TB',
            },
        ),
        (
            "HP Mini N100 8GB DDR4 128GB NVMe",
            {
                'cpu_model': 'N100',
                'generic_intel_core_type': None,
                'is_generic_intel_core_type': False,
                'ram': '8GB',
                'storage': '128GB',
            },
        ),
        (
            "ASUS Box Celeron 4GB RAM 64GB eMMC",
            {
                'cpu_model': 'CELERON',
                'generic_intel_core_type': None,
                'is_generic_intel_core_type': False,
                'ram': '4GB',
                'storage': '64GB',
            },
        ),
        (
            "SuperMicro Server NO CPU 32GB 2TB SSD",
            {
                'cpu_model': 'None',
                'generic_intel_core_type': 'None',
                'is_generic_intel_core_type': False,
                'ram': '32GB',
                'storage': '2TB',
            },
        ),
    ],
)
def test_parse_title(title, expected):
    parsed = parse_title(title)
    for key, value in expected.items():
        assert parsed[key] == value 