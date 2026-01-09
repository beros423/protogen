"""
Validation functions for data integrity checks
"""

import re


def validate_stock_location(stock_plate, stock_code):
    """Validate stock plate and location format
    
    Args:
        stock_plate: Stock plate identifier
        stock_code: Well location code (e.g., 'A1', 'H12')
        
    Returns:
        bool: True if valid, False otherwise
    """
    return stock_plate.strip() != "" and re.match(r'^[A-Ha-h][1-9]$|^[A-Ha-h]1[0-2]$', stock_code)


def validate_source_types(sources):
    """Validate that all required source types are present
    
    Args:
        sources: DataFrame with source information
        
    Returns:
        Tuple of (bool, list of missing types)
    """
    required_types = ['Promoter', 'CDS', 'Terminator', 'Connector']
    missing_types = []
    
    for type_item in required_types:
        if sources[sources['type'] == type_item].empty:
            missing_types.append(type_item)
    
    is_valid = len(missing_types) == 0
    return is_valid, missing_types
