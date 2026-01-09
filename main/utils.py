"""
Utility functions for assembly design tool
"""

import json


def find_source_well(sources_, name, required_volume):
    """Find source well with sufficient volume
    
    Args:
        sources_: DataFrame with source information (modified in place)
        name: Name of the part to find
        required_volume: Volume required
        
    Returns:
        Tuple of (plate, well)
        
    Raises:
        ValueError: If not enough volume available
    """
    sources_row = sources_[(sources_['name'] == name) & (sources_['volume'] >= required_volume)]
    if sources_row.empty:
        raise ValueError(f"Not enough volume available for '{name}'")
    row = sources_row.iloc[0]
    sources_.loc[(sources_['name'] == row['name']) & (sources_['plate'] == row['plate']) & (sources_['well'] == row['well']), 'volume'] -= required_volume
    return row['plate'], row['well']


def create_design_template_files():
    """Create template files for TU design import
    
    Returns:
        Tuple of (csv_template string, json_template dict)
    """
    # CSV template
    csv_template = """Group,Promoter,CDS,Terminator,Connector
Group_1,(P)TDH,(C)mTurquiose2,(T)ENO1,(Con)con1
Group_1,(P)RPL18B,(C)Venus,(T)ISSA1,(Con)con2
Group_1,(P)RAD27,(C)mRuby2,(T)ADH1,(Con)con1
Group_2,(P)CCW12,(C)Cas9,(T)PGK1,(Con)con3
Group_2,(P)ALD6,(C)I-Scei,(T)ENO2,(Con)con2"""
    
    # JSON template
    json_template = [
        {
            "group_name": "Group_1",
            "number_of_tu": 3,
            "designs": [
                {
                    "Promoter": ["(P)TDH"],
                    "CDS": ["(C)mTurquiose2"],
                    "Terminator": ["(T)ENO1"],
                    "Connector": ["(Con)con1"]
                },
                {
                    "Promoter": ["(P)RPL18B"],
                    "CDS": ["(C)Venus"],
                    "Terminator": ["(T)ISSA1"],
                    "Connector": ["(Con)con2"]
                },
                {
                    "Promoter": ["(P)RAD27"],
                    "CDS": ["(C)mRuby2"],
                    "Terminator": ["(T)ADH1"],
                    "Connector": ["(Con)con1"]
                }
            ]
        },
        {
            "group_name": "Group_2",
            "number_of_tu": 2,
            "designs": [
                {
                    "Promoter": ["(P)CCW12"],
                    "CDS": ["(C)Cas9"],
                    "Terminator": ["(T)PGK1"]
                },
                {
                    "Promoter": ["(P)ALD6"],
                    "CDS": ["(C)I-Scei (ORF)"],
                    "Terminator": ["(T)ENO2"]
                }
            ]
        }
    ]
    
    return csv_template, json_template
