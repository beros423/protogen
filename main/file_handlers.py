"""
File handling functions for loading various data formats
"""

import pandas as pd
import json
import base64
import io


def load_tu_design_from_csv(contents, filename):
    """Load TU design from uploaded CSV file
    
    Args:
        contents: Base64 encoded file contents
        filename: Name of the uploaded file
        
    Returns:
        List of design data dictionaries or None on error
    """
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        design_data = []
        unique_groups = df['Group'].unique()
        
        for group_name in unique_groups:
            group_df = df[df['Group'] == group_name]
            group_design = {
                'group_name': group_name,
                'number_of_tu': len(group_df),
                'designs': []
            }
            
            for _, row in group_df.iterrows():
                promoters = str(row.get('Promoter', '')).split(';') if pd.notna(row.get('Promoter')) else ['']
                cds_list = str(row.get('CDS', '')).split(';') if pd.notna(row.get('CDS')) else ['']
                terminators = str(row.get('Terminator', '')).split(';') if pd.notna(row.get('Terminator')) else ['']
                connectors = str(row.get('Connector', '')).split(';') if pd.notna(row.get('Connector')) else ['']
                
                promoters = [p.strip() for p in promoters if p.strip()]
                cds_list = [c.strip() for c in cds_list if c.strip()]
                terminators = [t.strip() for t in terminators if t.strip()]
                connectors = [c.strip() for c in connectors if c.strip()]
                
                tu_design = {
                    'Promoter': promoters,
                    'CDS': cds_list,
                    'Terminator': terminators,
                    'Connector': connectors,
                }
                group_design['designs'].append(tu_design)
            
            design_data.append(group_design)
        
        return design_data
    except Exception as e:
        print(f"Error loading TU design from CSV: {str(e)}")
        return None


def load_tu_design_from_json(contents, filename):
    """Load TU design from uploaded JSON file
    
    Args:
        contents: Base64 encoded file contents
        filename: Name of the uploaded file
        
    Returns:
        Design data as Python object or None on error
    """
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data = json.loads(decoded.decode('utf-8'))
        return data
    except Exception as e:
        print(f"Error loading TU design from JSON: {str(e)}")
        return None


def load_csv_sources(contents, filename):
    """Load sources from CSV file
    
    Args:
        contents: Base64 encoded file contents
        filename: Name of the uploaded file
        
    Returns:
        DataFrame with source data or None on error
    """
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), encoding='iso-8859-1')
        
        sources = pd.DataFrame(columns=["type", "name", "plate", "well", "volume", "note"])
        sources['type'] = df['type']
        sources['name'] = df['name']
        sources['plate'] = df['plate']
        sources['well'] = df['well']
        sources['volume'] = df['volume']
        sources['note'] = df['note']
        
        return sources
    except Exception as e:
        print(f"Error loading CSV sources: {str(e)}")
        return None


def load_excel_sources(uploaded_file, plate_names, default_vol):
    """Load sources from Excel file (legacy support)
    
    Args:
        uploaded_file: Path or file object
        plate_names: List of plate names
        default_vol: Default volume for sources
        
    Returns:
        Tuple of (sources DataFrame, sheet_names list)
    """
    sources = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    
    for i, sheet_name in enumerate(sheet_names):
        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        
        # Find starting position ('A' cell)
        for row_index in range(len(df_sheet)):
            for col_index in range(len(df_sheet.columns)):
                cell_value = df_sheet.iloc[row_index, col_index]
                if pd.notna(cell_value) and cell_value == 'A':
                    sr, sc = (row_index, col_index)
                    break

        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=sr, index_col=sc)
        for row_index, row in df_sheet.iterrows():
            for col_index, item in row.items():
                if pd.notna(item):
                    data = {
                        "type": "test",
                        "name": item,
                        "plate": plate_names[i].replace(" ", "_"),
                        "well": "".join([row_index, str(col_index)]),
                        "volume": default_vol,
                        "note": None
                    }
                    sources = pd.concat([sources, pd.DataFrame([data])])

    sources = sources.assign(type=sources['name'].apply(lambda x:
        'Promoter' if x.startswith('(P)') else
        'CDS' if x.startswith('(C)') else
        'Connector' if x.startswith('(N)') else
        'Terminator' if x.startswith('(T)') else
        None))
    
    return sources, sheet_names
