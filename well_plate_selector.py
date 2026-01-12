"""
Interactive Well Plate Selector Component for Dash
Uses Plotly to create a visual well plate with click selection
"""

import plotly.graph_objects as go
import numpy as np


def create_well_plate_figure(plate_type=96, selected_wells=None):
    """
    Create an interactive well plate visualization
    
    Args:
        plate_type: 96 or 384
        selected_wells: List of selected well names (e.g., ['A1', 'B2', 'C3'])
    
    Returns:
        Plotly figure object
    """
    if selected_wells is None:
        selected_wells = []
    
    # Define plate dimensions
    if plate_type == 96:
        rows = 8
        cols = 12
        row_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    elif plate_type == 384:
        rows = 16
        cols = 24
        row_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 
                      'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    else:
        raise ValueError("plate_type must be 96 or 384")
    
    # Create well names and positions
    well_names = []
    x_coords = []
    y_coords = []
    colors = []
    
    for row_idx, row_label in enumerate(row_labels[:rows]):
        for col_idx in range(1, cols + 1):
            well_name = f"{row_label}{col_idx}"
            well_names.append(well_name)
            x_coords.append(col_idx)
            y_coords.append(row_idx)
            
            # Color based on selection
            if well_name in selected_wells:
                colors.append('#00cc96')  # Green for selected
            else:
                colors.append('#e8e8e8')  # Light gray for unselected
    
    # Create scatter plot
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='markers+text',
        marker=dict(
            size=30 if plate_type == 96 else 15,
            color=colors,
            line=dict(color='#636363', width=2),
            symbol='circle'
        ),
        text=well_names,
        textposition='middle center',
        textfont=dict(
            size=8 if plate_type == 96 else 6,
            color='#2c3e50'
        ),
        hovertemplate='<b>%{text}</b><extra></extra>',
        customdata=well_names,
        name=''
    ))
    
    # Update layout
    fig.update_layout(
        xaxis=dict(
            showgrid=True,
            gridcolor='#e8e8e8',
            zeroline=False,
            range=[0.5, cols + 0.5],
            tickvals=list(range(1, cols + 1)),
            ticktext=[str(i) for i in range(1, cols + 1)],
            tickmode='array',
            fixedrange=True,  # Disable zoom/pan
            showticklabels=True,
            scaleanchor='y',  # Lock aspect ratio with y-axis
            scaleratio=1,  # 1:1 aspect ratio
            side='top',  # Position x-axis at top
            showline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e8e8e8',
            zeroline=False,
            autorange='reversed',
            range=[-0.5, rows - 0.5],
            tickvals=list(range(rows)),
            ticktext=row_labels[:rows],
            tickmode='array',
            fixedrange=True,  # Disable zoom/pan
            showticklabels=True,
            showline=False
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        width=600 if plate_type == 96 else 900,
        height=400 if plate_type == 96 else 600,
        hovermode='closest',
        showlegend=False,
        margin=dict(l=50, r=20, t=50, b=20),
        dragmode='select',  # Enable box selection
        selectdirection='any'  # Allow selection in any direction
    )
    
    return fig


def get_well_from_click(click_data):
    """
    Extract well name from click data
    
    Args:
        click_data: Dash clickData from dcc.Graph
    
    Returns:
        Well name (e.g., 'A1') or None
    """
    if click_data and 'points' in click_data:
        point = click_data['points'][0]
        if 'customdata' in point:
            return point['customdata']
    return None


def get_wells_from_selection(selected_data):
    """
    Extract well names from box/lasso selection data
    
    Args:
        selected_data: Dash selectedData from dcc.Graph
    
    Returns:
        List of well names (e.g., ['A1', 'A2', 'B1'])
    """
    if selected_data and 'points' in selected_data:
        wells = []
        for point in selected_data['points']:
            if 'customdata' in point:
                wells.append(point['customdata'])
        return wells
    return []


def toggle_well_selection(selected_wells, clicked_well):
    """
    Toggle a well's selection status
    
    Args:
        selected_wells: List of currently selected wells
        clicked_well: Well that was clicked
    
    Returns:
        Updated list of selected wells
    """
    if selected_wells is None:
        selected_wells = []
    
    if clicked_well in selected_wells:
        selected_wells.remove(clicked_well)
    else:
        selected_wells.append(clicked_well)
    
    return sorted(selected_wells, key=lambda x: (x[0], int(x[1:])))


def parse_wells_from_string(wells_string):
    """
    Parse well names from comma-separated string
    
    Args:
        wells_string: "A1, A2, B3, C4"
    
    Returns:
        List of well names
    """
    if not wells_string:
        return []
    
    wells = [w.strip().upper() for w in wells_string.split(',') if w.strip()]
    return wells


def format_wells_to_string(well_list):
    """
    Format well list to comma-separated string
    
    Args:
        well_list: List of well names
    
    Returns:
        "A1, A2, B3, C4"
    """
    if not well_list:
        return ""
    
    return ", ".join(well_list)
