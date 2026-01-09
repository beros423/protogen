import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table, ALL, MATCH
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import pandas as pd
from itertools import product
import json
from io import StringIO

# Import core functions from main module
from main import (
    load_tu_design_from_csv,
    load_tu_design_from_json,
    load_csv_sources,
    generate_protocol,
    protocol_to_ot2_script,
    create_ot2_labware_settings,
    validate_stock_location,
    validate_source_types,
    find_source_well,
    create_design_template_files
)

# Initialize Dash app with Bootstrap theme and Font Awesome
external_stylesheets = [
    dbc.themes.DARKLY,
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "ProtoGen - Assembly Design Tool"

# Layout Components
def create_step1_layout():
    """Step 1: Input Sources"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-upload me-3", style={"color": "#667eea"}),
                        "Step 1: Input Sources"
                    ], className="mb-2"),
                    html.P("Upload your source plate CSV file containing part information.", 
                           className="text-muted")
                ])
            ])
        ], className="mb-4"),
        
        # Upload Section
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Source Plate File", className="fw-bold mb-2"),
                        dcc.Upload(
                            id='upload-sources',
                            children=html.Div([
                                dbc.Button([
                                    html.I(className="fas fa-file-upload me-2"),
                                    "Select CSV File"
                                ], color="primary", size="lg", className="w-100")
                            ]),
                            multiple=False,
                            style={
                                'borderWidth': '2px',
                                'borderStyle': 'dashed',
                                'borderRadius': '10px',
                                'borderColor': '#4a5568',
                                'textAlign': 'center',
                                'padding': '20px',
                                'background': '#2d3748'
                            }
                        ),
                        html.Div(id='source-upload-status', className="mt-3")
                    ], md=12)
                ])
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # Preview Section
        dbc.Row([
            dbc.Col([
                html.Div(id='source-preview')
            ])
        ])
    ], fluid=True)

def create_step2_layout():
    """Step 2: Design"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-cog me-3", style={"color": "#667eea"}),
                        "Step 2: Design Configuration"
                    ], className="mb-2"),
                    html.P("Configure volume settings and design your TU assemblies.", 
                           className="text-muted")
                ])
            ])
        ], className="mb-4"),
        
        # Volume Settings
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-flask me-2"),
                    "Volume Settings"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Maximum Well Volume (μl)", className="fw-bold mb-2"),
                        dbc.Input(
                            id="lv1-maxvol", 
                            type="number", 
                            value=50.0, 
                            step=0.1, 
                            min=0,
                            className="form-control-lg"
                        ),
                        html.Small("Maximum volume for each TU", className="text-muted")
                    ], md=6),
                    dbc.Col([
                        html.Label("Dead Volume (μl)", className="fw-bold mb-2"),
                        dbc.Input(
                            id="lv2-deadvol", 
                            type="number", 
                            value=2.0, 
                            step=0.1, 
                            min=0,
                            className="form-control-lg"
                        ),
                        html.Small("Recommended ≥ 2μl", className="text-muted")
                    ], md=6)
                ], className="mb-4"),
                
                html.Hr(),
                
                html.H6("TU Parts Volumes", className="mb-3 fw-bold"),
                dbc.Row([
                    dbc.Col([
                        html.Label([html.I(className="fas fa-dna me-2"), "Promoter (μl)"], className="mb-2"),
                        dbc.Input(id="vol-promoter", type="number", value=2.0, step=0.1, min=0)
                    ], md=3),
                    dbc.Col([
                        html.Label([html.I(className="fas fa-dna me-2"), "CDS (μl)"], className="mb-2"),
                        dbc.Input(id="vol-cds", type="number", value=2.0, step=0.1, min=0)
                    ], md=3),
                    dbc.Col([
                        html.Label([html.I(className="fas fa-dna me-2"), "Terminator (μl)"], className="mb-2"),
                        dbc.Input(id="vol-terminator", type="number", value=2.0, step=0.1, min=0)
                    ], md=3),
                    dbc.Col([
                        html.Label([html.I(className="fas fa-link me-2"), "Connector (μl)"], className="mb-2"),
                        dbc.Input(id="vol-connector", type="number", value=2.0, step=0.1, min=0)
                    ], md=3)
                ])
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # TU Design Upload
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-file-import me-2"),
                    "Load TU Design from File (Optional)"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Upload Design File", className="fw-bold mb-2"),
                        dcc.Upload(
                            id='upload-design',
                            children=html.Div([
                                dbc.Button([
                                    html.I(className="fas fa-cloud-upload-alt me-2"),
                                    "Choose CSV/JSON File"
                                ], color="secondary", outline=True, className="w-100")
                            ]),
                            multiple=False
                        ),
                        html.Div(id='design-upload-status', className="mt-2")
                    ], md=6),
                    dbc.Col([
                        html.Label("Download Templates", className="fw-bold mb-2"),
                        dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-file-csv me-2"),
                                "CSV Template"
                            ], id="btn-csv-template", color="info", outline=True),
                            dbc.Button([
                                html.I(className="fas fa-file-code me-2"),
                                "JSON Template"
                            ], id="btn-json-template", color="info", outline=True)
                        ], className="w-100"),
                        dcc.Download(id="download-csv-template"),
                        dcc.Download(id="download-json-template")
                    ], md=6)
                ])
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # Groups Configuration
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-layer-group me-2"),
                    "Groups Configuration"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Number of Groups", className="fw-bold mb-2"),
                        dbc.Input(
                            id="num-groups", 
                            type="number", 
                            value=1, 
                            min=1, 
                            step=1,
                            className="form-control-lg"
                        )
                    ], md=4)
                ], className="mb-3"),
                html.Hr(),
                html.Div(id='groups-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # TU Design Details
        html.Div(id='tu-design-container'),
        
        # Design Summary
        html.Div(id='design-summary', className="mb-3")
    ], fluid=True)

def create_step3_layout():
    """Step 3: Set Commons"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-puzzle-piece me-3", style={"color": "#667eea"}),
                        "Step 3: Common Parts"
                    ], className="mb-2"),
                    html.P("Define common parts that will be included in all assemblies.", 
                           className="text-muted")
                ])
            ])
        ], className="mb-4"),
        
        # Lv1 Commons
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-layer-group me-2"),
                    "Level 1 Common Parts"
                ], className="mb-0 d-inline text-white"),
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-plus me-1"),
                        "Add"
                    ], id="btn-lv1-add", color="light", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-minus me-1"),
                        "Remove"
                    ], id="btn-lv1-remove", color="light", size="sm", outline=True)
                ], size="sm", className="float-end")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "These parts will be included in every Lv1 TU assembly."
                ], color="info", className="mb-3"),
                html.Div(id='lv1-commons-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        html.Div(id='lv1-total-volume', className="mb-4"),
        
        # Lv2 Commons
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-layer-group me-2"),
                    "Level 2 Common Parts"
                ], className="mb-0 d-inline text-white"),
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-plus me-1"),
                        "Add"
                    ], id="btn-lv2-add", color="light", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-minus me-1"),
                        "Remove"
                    ], id="btn-lv2-remove", color="light", size="sm", outline=True)
                ], size="sm", className="float-end")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "These parts will be included in every Lv2 output."
                ], color="info", className="mb-3"),
                html.Div(id='lv2-commons-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"})
    ], fluid=True)

def create_step4_layout():
    """Step 4: Results"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-chart-bar me-3", style={"color": "#667eea"}),
                        "Step 4: Results & Export"
                    ], className="mb-2"),
                    html.P("Review generated protocols and export to various formats.", 
                           className="text-muted")
                ])
            ])
        ], className="mb-4"),
        
        # Lv1 Results
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-vial me-2"),
                    "Level 1 Outputs"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Destination Plate Type", className="fw-bold mb-2"),
                        dcc.Dropdown(
                            id='lv1-plate-type',
                            options=[{'label': f'{x}-well plate', 'value': int(x)} for x in ["6", "12", "24", "48", "96", "384"]],
                            value=96,
                            className="mb-3",
                            style={'color': 'black'}
                        )
                    ], md=4)
                ]),
                html.Div(id='lv1-plate-names-container'),
                html.Div(id='lv1-results-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # Lv2 Results
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-vials me-2"),
                    "Level 2 Outputs"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Destination Plate Type", className="fw-bold mb-2"),
                        dcc.Dropdown(
                            id='lv2-plate-type',
                            options=[{'label': f'{x}-well plate', 'value': int(x)} for x in ["6", "12", "24", "48", "96", "384"]],
                            value=96,
                            className="mb-3",
                            style={'color': 'black'}
                        )
                    ], md=4)
                ]),
                html.Div(id='lv2-plate-names-container'),
                html.Div(id='lv2-results-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # OT2 Conversion
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-robot me-2"),
                    "Protocol Conversion"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Export Format", className="fw-bold mb-2"),
                        dcc.Dropdown(
                            id='convert-option',
                            options=[
                                {'label': 'None', 'value': 'none'},
                                {'label': 'OT2 Python Script', 'value': 'ot2'}
                            ],
                            value='none',
                            style={'color': 'black'},
                            className="mb-3"
                        )
                    ], md=4)
                ]),
                html.Div(id='ot2-conversion-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"})
    ], fluid=True)

# Main Layout
app.layout = html.Div([
    # Stores
    dcc.Store(id='sources-data'),
    dcc.Store(id='design-data'),
    dcc.Store(id='tu-selections-data'),
    dcc.Store(id='commons-data'),
    dcc.Store(id='lv1-commons-count', data=1),
    dcc.Store(id='lv2-commons-count', data=1),
    dcc.Store(id='lv1-protocol-data'),
    dcc.Store(id='lv2-protocol-data'),
    dcc.Store(id='lv1-outputs-data'),
    dcc.Store(id='lv2-outputs-data'),
    
    # Header
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1([
                        html.I(className="fas fa-dna me-3", style={"color": "#667eea"}),
                        "ProtoGen Assembly Design Tool"
                    ], className="text-center my-4", style={"font-weight": "700"}),
                    html.P([
                        html.I(className="fas fa-info-circle me-2"),
                        "Automated assembly design for synthetic biology projects"
                    ], className="text-center text-muted mb-4")
                ])
            ])
        ])
    ], fluid=True),
    
    # Main Content with Tabs
    dbc.Container([
        dbc.Row([
            # Left sidebar with vertical tabs
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="fas fa-dna me-2"),
                            html.H4("ProtoGen", className="d-inline mb-0")
                        ], className="text-center text-white")
                    ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
                    dbc.CardBody([
                        html.P("Navigation", className="text-muted small mb-3"),
                        dbc.Nav(
                            [
                                dbc.NavLink([
                                    html.Div([
                                        html.Span("1", className="badge bg-primary rounded-circle me-2", 
                                                 style={"width": "24px", "height": "24px", "display": "inline-flex", 
                                                       "align-items": "center", "justify-content": "center"}),
                                        html.Span("Input Sources")
                                    ])
                                ], href="#", id="nav-sources", active=True, className="mb-2"),
                                dbc.NavLink([
                                    html.Div([
                                        html.Span("2", className="badge bg-primary rounded-circle me-2", 
                                                 style={"width": "24px", "height": "24px", "display": "inline-flex", 
                                                       "align-items": "center", "justify-content": "center"}),
                                        html.Span("Design")
                                    ])
                                ], href="#", id="nav-design", className="mb-2"),
                                dbc.NavLink([
                                    html.Div([
                                        html.Span("3", className="badge bg-primary rounded-circle me-2", 
                                                 style={"width": "24px", "height": "24px", "display": "inline-flex", 
                                                       "align-items": "center", "justify-content": "center"}),
                                        html.Span("Set Commons")
                                    ])
                                ], href="#", id="nav-commons", className="mb-2"),
                                dbc.NavLink([
                                    html.Div([
                                        html.Span("4", className="badge bg-primary rounded-circle me-2", 
                                                 style={"width": "24px", "height": "24px", "display": "inline-flex", 
                                                       "align-items": "center", "justify-content": "center"}),
                                        html.Span("Results")
                                    ])
                                ], href="#", id="nav-results", className="mb-2")
                            ],
                            vertical=True,
                            pills=True
                        )
                    ], style={"padding": "20px"})
                ], className="shadow-sm", style={"border": "none", "border-radius": "15px", "background": "#1a202c"})
            ], md=3, lg=2, className="mb-4"),
            
            # Right content area
            dbc.Col([
                html.Div(create_step1_layout(), id='tab-sources-content', style={'display': 'block'}),
                html.Div(create_step2_layout(), id='tab-design-content', style={'display': 'none'}),
                html.Div(create_step3_layout(), id='tab-commons-content', style={'display': 'none'}),
                html.Div(create_step4_layout(), id='tab-results-content', style={'display': 'none'})
            ], md=9, lg=10)
        ])
    ], fluid=True, style={'padding': '0 20px 40px 20px'})
], style={'background': '#1a202c', 'min-height': '100vh'})

# Callbacks

# Navigation callback
@app.callback(
    [Output('tab-sources-content', 'style'),
     Output('tab-design-content', 'style'),
     Output('tab-commons-content', 'style'),
     Output('tab-results-content', 'style'),
     Output('nav-sources', 'active'),
     Output('nav-design', 'active'),
     Output('nav-commons', 'active'),
     Output('nav-results', 'active')],
    [Input('nav-sources', 'n_clicks'),
     Input('nav-design', 'n_clicks'),
     Input('nav-commons', 'n_clicks'),
     Input('nav-results', 'n_clicks')],
    prevent_initial_call=False
)
def update_tab_visibility(nav1, nav2, nav3, nav4):
    ctx = callback_context
    
    # Default: show sources tab
    styles = [
        {'display': 'block'},  # sources
        {'display': 'none'},   # design
        {'display': 'none'},   # commons
        {'display': 'none'}    # results
    ]
    active = [True, False, False, False]
    
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'nav-design':
            styles = [{'display': 'none'}, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}]
            active = [False, True, False, False]
        elif button_id == 'nav-commons':
            styles = [{'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'none'}]
            active = [False, False, True, False]
        elif button_id == 'nav-results':
            styles = [{'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'block'}]
            active = [False, False, False, True]
    
    return *styles, *active

@app.callback(
    Output('sources-data', 'data'),
    Output('source-upload-status', 'children'),
    Input('upload-sources', 'contents'),
    State('upload-sources', 'filename')
)
def upload_sources(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update
    
    sources = load_csv_sources(contents, filename)
    
    if sources is None:
        return None, dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Error loading file! Please check the file format."
        ], color="danger")
    
    status = dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        f"Successfully loaded {filename} ({len(sources)} parts)"
    ], color="success")
    
    return sources.to_json(date_format='iso', orient='split'), status

# Separate callback for source preview to persist across navigation
@app.callback(
    Output('source-preview', 'children'),
    Input('sources-data', 'data'),
    prevent_initial_call=False
)
def update_source_preview(sources_json):
    if sources_json is None:
        return ""
    
    try:
        sources = pd.read_json(sources_json, orient='split')
        
        preview = dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-table me-2"),
                    "Source Plate Preview"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dag.AgGrid(
                    id='source-grid',
                    rowData=sources.to_dict('records'),
                    columnDefs=[
                        {
                            'field': col,
                            'headerName': col,
                            'filter': True,
                            'sortable': True,
                            'resizable': True,
                            'editable': False,
                            'wrapText': True,
                            'autoHeight': True,
                            'flex': 1 if col in ['name', 'plate'] else 0,
                            'minWidth': 100
                        } for col in sources.columns
                    ],
                    defaultColDef={
                        'filter': True,
                        'sortable': True,
                        'resizable': True,
                        'minWidth': 100
                    },
                    dashGridOptions={
                        'pagination': True,
                        'paginationPageSize': 20,
                        'paginationPageSizeSelector': [10, 20, 50, 100],
                        'domLayout': 'autoHeight',
                        'enableCellTextSelection': True,
                        'ensureDomOrder': True,
                        'rowSelection': 'multiple',
                        'animateRows': True
                    },
                    className='ag-theme-alpine-dark',
                    style={'height': '600px', 'width': '100%'}
                )
            ], style={'padding': '0'})
        ], className="shadow-sm mt-3", style={"border": "none", "border-radius": "15px"})
        
        return preview
    except:
        return ""

@app.callback(
    Output('download-csv-template', 'data'),
    Input('btn-csv-template', 'n_clicks'),
    prevent_initial_call=True
)
def download_csv_template(n_clicks):
    csv_template, _ = create_design_template_files()
    return dict(content=csv_template, filename="tu_design_template.csv")

@app.callback(
    Output('download-json-template', 'data'),
    Input('btn-json-template', 'n_clicks'),
    prevent_initial_call=True
)
def download_json_template(n_clicks):
    _, json_template = create_design_template_files()
    json_str = json.dumps(json_template, indent=2)
    return dict(content=json_str, filename="tu_design_template.json")

@app.callback(
    Output('groups-container', 'children', allow_duplicate=True),
    Input('num-groups', 'value'),
    State('design-data', 'data'),
    prevent_initial_call=True
)
def update_groups(num_groups, design_data_json):
    """Update groups when manually changing number of groups (not from design upload)"""
    ctx = callback_context
    
    # If we have design data from a recent upload, don't override
    # This prevents this callback from overwriting the upload_design callback's output
    if design_data_json:
        try:
            design_data = json.loads(design_data_json)
            # If design data has the same number of groups, it means upload just happened
            if len(design_data) == num_groups:
                # print(f"[DEBUG] Skipping update_groups - design data already loaded with {num_groups} groups")
                return dash.no_update
        except:
            pass
    
    if num_groups is None:
        num_groups = 1
    
    # print(f"[DEBUG] update_groups creating {num_groups} default groups")
    
    groups = []
    for i in range(num_groups):
        group = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([
                            html.I(className="fas fa-folder me-2", style={"color": "#667eea"}),
                            f"Group {i+1}"
                        ], className="fw-bold")
                    ], width=2),
                    dbc.Col([
                        html.Label("Group Name", className="small text-muted mb-1"),
                        dbc.Input(
                            id={'type': 'group-name', 'index': i}, 
                            type="text", 
                            value=f"Group_{i+1}", 
                            placeholder="Enter group name",
                            size="sm"
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Number of TUs", className="small text-muted mb-1"),
                        dbc.Input(
                            id={'type': 'group-nop', 'index': i}, 
                            type="number", 
                            value=3, 
                            min=1, 
                            step=1,
                            size="sm"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Repeats", className="small text-muted mb-1"),
                        dbc.Input(
                            id={'type': 'group-roa', 'index': i}, 
                            type="number", 
                            value=1, 
                            min=1, 
                            step=1, 
                            disabled=True,
                            size="sm"
                        )
                    ], width=3)
                ])
            ])
        ], className="mb-3 shadow-sm", style={"border": "1px solid #4a5568", "border-radius": "10px", "background": "#2d3748"})
        groups.append(group)
    
    return groups

# Callback for design file upload
@app.callback(
    Output('design-data', 'data'),
    Output('design-upload-status', 'children'),
    Output('num-groups', 'value'),
    Output('groups-container', 'children'),
    Input('upload-design', 'contents'),
    State('upload-design', 'filename')
)
def upload_design(contents, filename):
    if contents is None:
        return None, "", None, []
    
    file_extension = filename.split('.')[-1].lower() if filename else ''
    
    if file_extension == 'csv':
        design_data = load_tu_design_from_csv(contents, filename)
    elif file_extension == 'json':
        design_data = load_tu_design_from_json(contents, filename)
    else:
        return None, dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Unsupported file format. Please upload CSV or JSON files."
        ], color="danger"), None, []
    
    if design_data is None:
        return None, dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Error loading design file!"
        ], color="danger"), None, []
    
    # Parse design data to extract group information
    num_groups = len(design_data)
    groups = []
    
    # print(f"[DEBUG] Loaded design data: {design_data}")  # Debug output
    
    for i, group_info in enumerate(design_data):
        group_name = group_info.get('group_name', f'Group_{i+1}')
        # Handle both 'tus' and 'designs' keys for backward compatibility
        tus_list = group_info.get('tus', group_info.get('designs', []))
        
        # Calculate number of TUs - prioritize actual TU list length
        if tus_list and len(tus_list) > 0:
            num_tus = len(tus_list)
        else:
            num_tus = group_info.get('number_of_tu', 1)
        
        roa = group_info.get('roa', 1)
        
        # print(f"[DEBUG] Group {i}: name={group_name}, tus_list length={len(tus_list) if tus_list else 0}, num_tus={num_tus}, roa={roa}")  # Debug output
        
        group = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([
                            html.I(className="fas fa-folder me-2", style={"color": "#667eea"}),
                            f"Group {i+1}"
                        ], className="fw-bold")
                    ], width=2),
                    dbc.Col([
                        html.Label("Group Name", className="small text-muted mb-1"),
                        dbc.Input(
                            id={'type': 'group-name', 'index': i}, 
                            type="text", 
                            value=group_name, 
                            placeholder="Enter group name",
                            size="sm"
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Number of TUs", className="small text-muted mb-1"),
                        dbc.Input(
                            id={'type': 'group-nop', 'index': i}, 
                            type="number", 
                            value=num_tus, 
                            min=1, 
                            step=1,
                            size="sm"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Repeats", className="small text-muted mb-1"),
                        dbc.Input(
                            id={'type': 'group-roa', 'index': i}, 
                            type="number", 
                            value=roa, 
                            min=1, 
                            step=1, 
                            disabled=True,
                            size="sm"
                        )
                    ], width=3)
                ])
            ])
        ], className="mb-3 shadow-sm", style={"border": "1px solid #4a5568", "border-radius": "10px", "background": "#2d3748"})
        groups.append(group)
    
    status = dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        f"Successfully loaded design from {filename}"
    ], color="success")
    
    return json.dumps(design_data), status, num_groups, groups

# Callback for TU Design Details
@app.callback(
    Output('tu-design-container', 'children'),
    Output('design-summary', 'children'),
    [Input({'type': 'group-name', 'index': ALL}, 'value'),
     Input({'type': 'group-nop', 'index': ALL}, 'value'),
     Input('design-data', 'data')],
    [State('sources-data', 'data'),
     State('tu-selections-data', 'data')]
)
def update_tu_design(group_names, group_nops, design_data_json, sources_json, tu_selections_json):
    """Generate TU design details for each group"""
    if not group_names or not group_nops:
        return [], ""
    
    # Parse sources to get available parts by type
    parts_by_type = {
        'Promoter': [],
        'CDS': [],
        'Terminator': [],
        'Connector': []
    }
    
    if sources_json:
        try:
            sources_df = pd.read_json(sources_json, orient='split')
            for part_type in parts_by_type.keys():
                if part_type == 'Connector':
                    # Special handling for Connector ordering (matching protogen.py logic)
                    connector_sources = sources_df[sources_df['type'] == 'Connector']['name'].drop_duplicates().sort_values().tolist()
                    # Separate ex connectors (start with '(N)s' or end with 'e')
                    connector_ex = [c for c in connector_sources if c.startswith('(N)s') or c.endswith('e')]
                    connector_ex = sorted(connector_ex, key=lambda x: [0 if c.isalpha() else 1 for c in x])
                    # Endo connectors (rest)
                    connector_endo = [c for c in connector_sources if c not in connector_ex]
                    # Final order: ex + endo
                    parts_by_type['Connector'] = connector_ex + connector_endo
                else:
                    parts_by_type[part_type] = sources_df[sources_df['type'] == part_type]['name'].unique().tolist()
        except Exception as e:
            print(f"Error parsing sources: {e}")
    
    # Parse saved TU selections
    saved_selections = None
    if tu_selections_json:
        try:
            saved_selections = json.loads(tu_selections_json)
            # print(f"[DEBUG] Loaded saved TU selections")
        except Exception as e:
            print(f"Error parsing saved selections: {e}")
    
    # Parse design data if available
    design_data = None
    if design_data_json:
        try:
            design_data = json.loads(design_data_json)
            # print(f"[DEBUG] Loaded design data")
        except Exception as e:
            print(f"Error parsing design data: {e}")
    
    tu_designs = []
    total_tus = 0
    global_tu_idx = 0  # Track global TU index across all groups
    
    for group_idx, (group_name, num_tus) in enumerate(zip(group_names, group_nops)):
        if num_tus is None or num_tus < 1:
            continue
            
        total_tus += num_tus
        
        # Create TU design UI for this group
        tus = []
        for tu_idx in range(num_tus):
            # Priority: 1. Design data (uploaded file), 2. Saved selections, 3. Empty
            default_promoter = []
            default_cds = []
            default_terminator = []
            default_connector = None  # Single value for connector
            
            # First, try to load from design data (if user uploaded a design file)
            if design_data and group_idx < len(design_data):
                # Handle both 'tus' and 'designs' keys
                group_tus = design_data[group_idx].get('tus', design_data[group_idx].get('designs', []))
                if tu_idx < len(group_tus):
                    tu_parts = group_tus[tu_idx]
                    # Handle list or string values - convert to list for multi-select
                    promoter_val = tu_parts.get('Promoter', [])
                    default_promoter = promoter_val if isinstance(promoter_val, list) else ([promoter_val] if promoter_val else [])
                    
                    cds_val = tu_parts.get('CDS', [])
                    default_cds = cds_val if isinstance(cds_val, list) else ([cds_val] if cds_val else [])
                    
                    terminator_val = tu_parts.get('Terminator', [])
                    default_terminator = terminator_val if isinstance(terminator_val, list) else ([terminator_val] if terminator_val else [])
                    
                    # Connector: single value
                    connector_val = tu_parts.get('Connector', None)
                    if isinstance(connector_val, list) and connector_val:
                        default_connector = connector_val[0]  # Take first element if list
                    else:
                        default_connector = connector_val if connector_val else None
                    # print(f"[DEBUG] Loaded TU {global_tu_idx} from design data")
            # Otherwise, try to load from saved selections
            elif saved_selections and global_tu_idx < len(saved_selections.get('promoters', [])):
                # Saved selections might be strings or lists - convert to list
                prom = saved_selections['promoters'][global_tu_idx]
                default_promoter = prom if isinstance(prom, list) else ([prom] if prom else [])
                
                cds = saved_selections['cds'][global_tu_idx]
                default_cds = cds if isinstance(cds, list) else ([cds] if cds else [])
                
                term = saved_selections['terminators'][global_tu_idx]
                default_terminator = term if isinstance(term, list) else ([term] if term else [])
                
                # Connector: single value
                conn = saved_selections['connectors'][global_tu_idx]
                if isinstance(conn, list) and conn:
                    default_connector = conn[0]  # Take first element if list
                elif isinstance(conn, str) and conn:
                    default_connector = conn
                else:
                    default_connector = None
                # print(f"[DEBUG] Restored TU {global_tu_idx} from saved selections, connector={default_connector}")
            
            # Auto-assign connector if not already set (following protogen.py logic)
            if not default_connector and parts_by_type['Connector']:
                # print(f"[DEBUG] Auto-assigning connector for TU {global_tu_idx} (group {group_idx}, tu {tu_idx}/{num_tus})")
                connector_list = parts_by_type['Connector']
                # print(f"[DEBUG] Connector list: {connector_list}")
                # Separate ex and endo connectors
                connector_ex = [c for c in connector_list if c.startswith('(N)s') or c.endswith('e')]
                connector_endo = [c for c in connector_list if c not in connector_ex]
                # print(f"[DEBUG] Ex connectors: {connector_ex}, Endo connectors: {connector_endo}")
                
                # Assignment logic based on TU position within group
                if tu_idx == 0:  # First TU in group
                    default_connector = connector_ex[0] if connector_ex else connector_list[0]
                elif tu_idx == num_tus - 1:  # Last TU in group
                    default_connector = connector_ex[tu_idx] if tu_idx < len(connector_ex) else (connector_list[tu_idx % len(connector_list)] if connector_list else None)
                else:  # Middle TUs
                    endo_idx = tu_idx - 1
                    default_connector = connector_endo[endo_idx] if endo_idx < len(connector_endo) else (connector_list[tu_idx % len(connector_list)] if connector_list else None)
                
                # print(f"[DEBUG] Auto-assigned connector for TU {global_tu_idx} (group {group_idx}, tu {tu_idx}): {default_connector}")
            
            tu_row = dbc.Row([
                dbc.Col([
                    html.Label(f"TU {tu_idx + 1}", className="small fw-bold text-center")
                ], width=1),
                dbc.Col([
                    dcc.Dropdown(
                        id={'type': 'tu-promoter', 'group': group_idx, 'tu': tu_idx},
                        options=[{'label': p, 'value': p} for p in parts_by_type['Promoter']],
                        value=default_promoter,
                        placeholder="Select Promoter(s)",
                        multi=True,
                        style={'fontSize': '14px', 'color': 'black'}
                    )
                ], width=2),
                dbc.Col([
                    dcc.Dropdown(
                        id={'type': 'tu-cds', 'group': group_idx, 'tu': tu_idx},
                        options=[{'label': p, 'value': p} for p in parts_by_type['CDS']],
                        value=default_cds,
                        placeholder="Select CDS",
                        multi=True,
                        style={'fontSize': '14px', 'color': 'black'}
                    )
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id={'type': 'tu-terminator', 'group': group_idx, 'tu': tu_idx},
                        options=[{'label': p, 'value': p} for p in parts_by_type['Terminator']],
                        value=default_terminator,
                        placeholder="Select Terminator(s)",
                        multi=True,
                        style={'fontSize': '14px', 'color': 'black'}
                    )
                ], width=2),
                dbc.Col([
                    dcc.Dropdown(
                        id={'type': 'tu-connector', 'group': group_idx, 'tu': tu_idx},
                        options=[{'label': p, 'value': p} for p in parts_by_type['Connector']],
                        value=default_connector,
                        placeholder="Connector (Auto-assigned)",
                        disabled=False,
                        style={'fontSize': '14px', 'color': 'black'}
                    )
                ], width=3)
            ], className="mb-2")
            tus.append(tu_row)
            global_tu_idx += 1  # Increment global TU index
        
        group_card = dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-folder me-2", style={"color": "#68d391"}),
                    f"{group_name or f'Group {group_idx + 1}'} - TU Design"
                ], className="mb-0")
            ], style={"background": "#2d3748"}),
            dbc.CardBody([
                # Header row
                dbc.Row([
                    dbc.Col(html.Label("TU", className="small fw-bold text-muted text-center"), width=1),
                    dbc.Col(html.Label("Promoter", className="small fw-bold text-muted"), width=2),
                    dbc.Col(html.Label("CDS", className="small fw-bold text-muted"), width=3),
                    dbc.Col(html.Label("Terminator", className="small fw-bold text-muted"), width=2),
                    dbc.Col(html.Label("Connector", className="small fw-bold text-muted"), width=3)
                ], className="mb-2"),
                # TU rows
                html.Div(tus)
            ])
        ], className="mb-3 shadow-sm", style={"border": "1px solid #4a5568", "border-radius": "10px", "background": "#1a202c"})
        
        tu_designs.append(group_card)
    
    # Create summary
    summary = dbc.Alert([
        html.I(className="fas fa-info-circle me-2"),
        f"Total: {len(group_names)} group(s), {total_tus} TU(s)"
    ], color="info") if total_tus > 0 else ""
    
    return tu_designs, summary

# Callback to save TU selections
@app.callback(
    Output('tu-selections-data', 'data'),
    [Input({'type': 'tu-promoter', 'group': ALL, 'tu': ALL}, 'value'),
     Input({'type': 'tu-cds', 'group': ALL, 'tu': ALL}, 'value'),
     Input({'type': 'tu-terminator', 'group': ALL, 'tu': ALL}, 'value'),
     Input({'type': 'tu-connector', 'group': ALL, 'tu': ALL}, 'value')],
    prevent_initial_call=True
)
def save_tu_selections(promoters, cds_list, terminators, connectors):
    """Save user's TU part selections to store"""
    if not promoters:
        return None
    
    selections = {
        'promoters': promoters,
        'cds': cds_list,
        'terminators': terminators,
        'connectors': connectors
    }
    
    # print(f"[DEBUG] Saving TU selections: {len(promoters)} TUs")
    return json.dumps(selections)

# Callbacks for Lv1 Commons
@app.callback(
    Output('lv1-commons-count', 'data'),
    Input('btn-lv1-add', 'n_clicks'),
    Input('btn-lv1-remove', 'n_clicks'),
    State('lv1-commons-count', 'data'),
    prevent_initial_call=True
)
def update_lv1_commons_count(add_clicks, remove_clicks, current_count):
    ctx = callback_context
    if not ctx.triggered:
        return current_count
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-lv1-add':
        return current_count + 1
    elif button_id == 'btn-lv1-remove' and current_count > 1:
        return current_count - 1
    
    return current_count

@app.callback(
    Output('lv1-commons-container', 'children'),
    [Input('lv1-commons-count', 'data'),
     Input('sources-data', 'data')]
)
def update_lv1_commons_fields(count, sources_json):
    if count is None:
        count = 1
    
    # Parse sources if available
    sources_list = []
    if sources_json:
        try:
            sources_df = pd.read_json(sources_json, orient='split')
            sources_list = sources_df['name'].unique().tolist()
        except:
            pass
    
    fields = []
    for i in range(count):
        field = dbc.Row([
            dbc.Col([
                html.Label(f"Part {i+1}", className="small fw-bold mb-1"),
                dcc.Dropdown(
                    id={'type': 'lv1-common-name', 'index': i},
                    options=[{'label': s, 'value': s} for s in sources_list],
                    value="GGAmixture" if i == 0 else None,
                    placeholder="Select or type part name",
                    searchable=True,
                    clearable=True,
                    style={'fontSize': '14px', 'color': 'black'}
                )
            ], md=4),
            dbc.Col([
                html.Label("Volume (μl)", className="small text-muted mb-1"),
                dbc.Input(
                    id={'type': 'lv1-common-volume', 'index': i},
                    type="number",
                    value=2.0,
                    step=0.1,
                    min=0,
                    size="sm"
                )
            ], md=2),
            dbc.Col([
                html.Label("Source Plate", className="small text-muted mb-1"),
                dbc.Input(
                    id={'type': 'lv1-common-plate', 'index': i},
                    type="text",
                    placeholder="Plate name",
                    value="GGAmix_plate" if i == 0 else "",
                    size="sm"
                )
            ], md=3),
            dbc.Col([
                html.Label("Well", className="small text-muted mb-1"),
                dbc.Input(
                    id={'type': 'lv1-common-well', 'index': i},
                    type="text",
                    placeholder="A1",
                    value="A1",
                    size="sm"
                )
            ], md=3)
        ], className="mb-3")
        fields.append(field)
    
    return fields

# Callbacks for Lv2 Commons
@app.callback(
    Output('lv2-commons-count', 'data'),
    Input('btn-lv2-add', 'n_clicks'),
    Input('btn-lv2-remove', 'n_clicks'),
    State('lv2-commons-count', 'data'),
    prevent_initial_call=True
)
def update_lv2_commons_count(add_clicks, remove_clicks, current_count):
    ctx = callback_context
    if not ctx.triggered:
        return current_count
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-lv2-add':
        return current_count + 1
    elif button_id == 'btn-lv2-remove' and current_count > 1:
        return current_count - 1
    
    return current_count

@app.callback(
    Output('lv2-commons-container', 'children'),
    [Input('lv2-commons-count', 'data'),
     Input('sources-data', 'data')]
)
def update_lv2_commons_fields(count, sources_json):
    if count is None:
        count = 1
    
    # Parse sources if available
    sources_list = []
    if sources_json:
        try:
            sources_df = pd.read_json(sources_json, orient='split')
            sources_list = sources_df['name'].unique().tolist()
        except:
            pass
    
    fields = []
    for i in range(count):
        field = dbc.Row([
            dbc.Col([
                html.Label(f"Part {i+1}", className="small fw-bold mb-1"),
                dcc.Dropdown(
                    id={'type': 'lv2-common-name', 'index': i},
                    options=[{'label': s, 'value': s} for s in sources_list],
                    value="Vector" if i == 0 else None,
                    placeholder="Select or type part name",
                    searchable=True,
                    clearable=True,
                    style={'fontSize': '14px', 'color': 'black'}
                )
            ], md=4),
            dbc.Col([
                html.Label("Volume (μl)", className="small text-muted mb-1"),
                dbc.Input(
                    id={'type': 'lv2-common-volume', 'index': i},
                    type="number",
                    value=10.0,
                    step=0.1,
                    min=0,
                    size="sm"
                )
            ], md=2),
            dbc.Col([
                html.Label("Source Plate", className="small text-muted mb-1"),
                dbc.Input(
                    id={'type': 'lv2-common-plate', 'index': i},
                    type="text",
                    placeholder="Plate name",
                    value="Vector_plate" if i == 0 else "",
                    size="sm"
                )
            ], md=3),
            dbc.Col([
                html.Label("Well", className="small text-muted mb-1"),
                dbc.Input(
                    id={'type': 'lv2-common-well', 'index': i},
                    type="text",
                    placeholder="A1",
                    value="A1",
                    size="sm"
                )
            ], md=3)
        ], className="mb-3")
        fields.append(field)
    
    return fields

# Callback for total volume calculation
@app.callback(
    Output('lv1-total-volume', 'children'),
    Input({'type': 'lv1-common-volume', 'index': ALL}, 'value'),
    State('vol-promoter', 'value'),
    State('vol-cds', 'value'),
    State('vol-terminator', 'value'),
    State('vol-connector', 'value')
)
def calculate_lv1_total_volume(lv1_volumes, vol_p, vol_c, vol_t, vol_n):
    if not lv1_volumes:
        lv1_volumes = [0]
    
    vols = [vol_p or 0, vol_c or 0, vol_t or 0, vol_n or 0]
    tu_parts_vol = sum(vols)
    commons_vol = sum([v for v in lv1_volumes if v is not None])
    total_vol = tu_parts_vol + commons_vol
    
    return dbc.Alert([
        html.I(className="fas fa-calculator me-2"),
        html.Strong(f"Total Lv1 Volume: "),
        f"{total_vol:.1f} μl per TU ",
        html.Small(f"(TU parts: {tu_parts_vol:.1f} μl + Commons: {commons_vol:.1f} μl)", className="text-muted")
    ], color="info")

# Callback to generate protocols when navigating to Step 4
@app.callback(
    [Output('lv1-protocol-data', 'data'),
     Output('lv1-outputs-data', 'data'),
     Output('lv2-protocol-data', 'data'),
     Output('lv2-outputs-data', 'data')],
    [Input('nav-results', 'n_clicks')],
    [State('sources-data', 'data'),
     State('vol-promoter', 'value'),
     State('vol-cds', 'value'),
     State('vol-terminator', 'value'),
     State('vol-connector', 'value'),
     State({'type': 'lv1-common-name', 'index': ALL}, 'value'),
     State({'type': 'lv1-common-volume', 'index': ALL}, 'value'),
     State({'type': 'lv1-common-plate', 'index': ALL}, 'value'),
     State({'type': 'lv1-common-well', 'index': ALL}, 'value'),
     State({'type': 'lv2-common-name', 'index': ALL}, 'value'),
     State({'type': 'lv2-common-volume', 'index': ALL}, 'value'),
     State({'type': 'lv2-common-plate', 'index': ALL}, 'value'),
     State({'type': 'lv2-common-well', 'index': ALL}, 'value'),
     State({'type': 'group-name', 'index': ALL}, 'value'),
     State({'type': 'group-nop', 'index': ALL}, 'value'),
     State({'type': 'tu-promoter', 'group': ALL, 'tu': ALL}, 'value'),
     State({'type': 'tu-cds', 'group': ALL, 'tu': ALL}, 'value'),
     State({'type': 'tu-terminator', 'group': ALL, 'tu': ALL}, 'value'),
     State({'type': 'tu-connector', 'group': ALL, 'tu': ALL}, 'value')],
    prevent_initial_call=True
)
def generate_all_protocols(nav_clicks, sources_json, vol_p, vol_c, vol_t, vol_n,
                          lv1_names, lv1_vols, lv1_plates, lv1_wells,
                          lv2_names, lv2_vols, lv2_plates, lv2_wells,
                          group_names, group_nops,
                          tu_promoters, tu_cds_list, tu_terminators, tu_connectors):
    
    if not sources_json:
        return None, None, None, None
    
    try:
        # Load sources
        sources = pd.read_json(sources_json, orient='split')
        sources_copy = sources.copy()
        
        # Build Lv1 commons
        lv1_commons = []
        for i, name in enumerate(lv1_names):
            if name and lv1_vols[i]:
                lv1_commons.append({
                    'name': name,
                    'volume': lv1_vols[i],
                    'plate': lv1_plates[i] if i < len(lv1_plates) else '',
                    'well': lv1_wells[i] if i < len(lv1_wells) else 'A1'
                })
        
        # Add lv1 commons to sources if not exist
        for common in lv1_commons:
            if common['name'] not in sources_copy['name'].values:
                new_row = pd.DataFrame([{
                    'type': 'common',
                    'name': common['name'],
                    'plate': common['plate'],
                    'well': common['well'],
                    'volume': 100000,
                    'note': 'added'
                }])
                sources_copy = pd.concat([sources_copy, new_row], ignore_index=True)
        
        # Build Lv1 designs from TU part selections
        vols = [vol_p or 2.0, vol_c or 2.0, vol_t or 2.0, vol_n or 2.0]
        lv1_designs = []
        
        # Check if we have TU design data
        if tu_promoters and tu_cds_list and tu_terminators and tu_connectors:
            # Build designs from selected parts
            for tu_idx in range(len(tu_promoters)):
                promoter_list = tu_promoters[tu_idx]
                cds_list_val = tu_cds_list[tu_idx]
                terminator_list = tu_terminators[tu_idx]
                connector_val = tu_connectors[tu_idx]  # Single value, not a list
                
                # Convert to list if not already (for backward compatibility)
                if not isinstance(promoter_list, list):
                    promoter_list = [promoter_list] if promoter_list else []
                if not isinstance(cds_list_val, list):
                    cds_list_val = [cds_list_val] if cds_list_val else []
                if not isinstance(terminator_list, list):
                    terminator_list = [terminator_list] if terminator_list else []
                
                # Skip if any part is not selected
                if not all([promoter_list, cds_list_val, terminator_list, connector_val]):
                    continue
                
                # Determine which group this TU belongs to
                group_idx = 0
                tu_count = 0
                for g_idx, nop in enumerate(group_nops or []):
                    if tu_count + (nop or 0) > tu_idx:
                        group_idx = g_idx
                        break
                    tu_count += (nop or 0)
                
                group_name = group_names[group_idx] if group_idx < len(group_names) else f'Group_{group_idx + 1}'
                
                # Create design with first selected part from each list
                # Connector is single value (auto-assigned by TU index)
                design = [
                    {'name': promoter_list[0], 'volume': vols[0], 'note': group_name},
                    {'name': cds_list_val[0], 'volume': vols[1], 'note': group_name},
                    {'name': terminator_list[0], 'volume': vols[2], 'note': group_name},
                    {'name': connector_val, 'volume': vols[3], 'note': group_name}
                ]
                for common in lv1_commons:
                    design.append({'name': common['name'], 'volume': common['volume'], 'note': group_name})
                lv1_designs.append(design)
        else:
            # Fallback: Create simple designs based on available parts
            promoters = sources[sources['type'] == 'Promoter']['name'].tolist()[:2]
            cds_list = sources[sources['type'] == 'CDS']['name'].tolist()[:2]
            terminators = sources[sources['type'] == 'Terminator']['name'].tolist()[:2]
            connectors = sources[sources['type'] == 'Connector']['name'].tolist()[:2]
            
            for i in range(min(2, len(promoters))):
                design = [
                    {'name': promoters[i] if i < len(promoters) else promoters[0], 'volume': vols[0], 'note': group_names[0] if group_names else 'Group_1'},
                    {'name': cds_list[i] if i < len(cds_list) else cds_list[0], 'volume': vols[1], 'note': group_names[0] if group_names else 'Group_1'},
                    {'name': terminators[i] if i < len(terminators) else terminators[0], 'volume': vols[2], 'note': group_names[0] if group_names else 'Group_1'},
                    {'name': connectors[i] if i < len(connectors) else connectors[0], 'volume': vols[3], 'note': group_names[0] if group_names else 'Group_1'}
                ]
                for common in lv1_commons:
                    design.append({'name': common['name'], 'volume': common['volume'], 'note': group_names[0] if group_names else 'Group_1'})
                lv1_designs.append(design)
        
        # Generate Lv1 protocol
        lv1_dest = ['Lv1_destination_1']
        lv1_protocol, lv1_outputs = generate_protocol(lv1_designs, lv1_dest, sources_copy.copy(), plate_type=96, naming="TU")
        
        if lv1_protocol is None:
            return None, None, None, None
        
        # Build Lv2 commons
        lv2_commons = []
        for i, name in enumerate(lv2_names):
            if name and lv2_vols[i]:
                lv2_commons.append({
                    'name': name,
                    'volume': lv2_vols[i],
                    'plate': lv2_plates[i] if i < len(lv2_plates) else '',
                    'well': lv2_wells[i] if i < len(lv2_wells) else 'A1'
                })
        
        # Add lv2 commons to sources
        lv2_sources = pd.concat([sources_copy, lv1_outputs])
        for common in lv2_commons:
            if common['name'] not in lv2_sources['name'].values:
                new_row = pd.DataFrame([{
                    'type': 'common',
                    'name': common['name'],
                    'plate': common['plate'],
                    'well': common['well'],
                    'volume': 100000,
                    'note': 'added'
                }])
                lv2_sources = pd.concat([lv2_sources, new_row], ignore_index=True)
        
        # Build Lv2 designs
        total_vol = sum(vols) + sum([c['volume'] for c in lv1_commons])
        lv2_designs = []
        
        design = []
        for idx, row in lv1_outputs.iterrows():
            design.append({'name': row['name'], 'volume': total_vol, 'note': group_names[0] if group_names else 'Group_1'})
        for common in lv2_commons:
            design.append({'name': common['name'], 'volume': common['volume'], 'note': group_names[0] if group_names else 'Group_1'})
        lv2_designs.append(design)
        
        # Generate Lv2 protocol
        lv2_dest = ['Lv2_destination_1']
        lv2_protocol, lv2_outputs = generate_protocol(lv2_designs, lv2_dest, lv2_sources, plate_type=96, naming=None)
        
        return (lv1_protocol.to_json(orient='split') if lv1_protocol is not None else None,
                lv1_outputs.to_json(orient='split') if lv1_outputs is not None else None,
                lv2_protocol.to_json(orient='split') if lv2_protocol is not None else None,
                lv2_outputs.to_json(orient='split') if lv2_outputs is not None else None)
        
    except Exception as e:
        print(f"Error generating protocols: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None

# Callback to display Lv1 results
@app.callback(
    Output('lv1-results-container', 'children'),
    [Input('lv1-protocol-data', 'data'),
     Input('lv1-outputs-data', 'data')]
)
def display_lv1_results(lv1_protocol_json, lv1_outputs_json):
    if not lv1_protocol_json:
        return dbc.Alert([
            # html.I(className="fas fa-info-circle me-2"),
            "Please complete Steps 1-3 and click on Results to generate protocols."
        ], color="info")
    try:
        lv1_protocol = pd.read_json(StringIO(lv1_protocol_json), orient='split')
        lv1_outputs = pd.read_json(StringIO(lv1_outputs_json), orient='split')
        
        # Rename columns with dots to underscores for AG Grid compatibility
        lv1_protocol.columns = [str(col).replace('.', '_') for col in lv1_protocol.columns]
        lv1_outputs.columns = [str(col).replace('.', '_') for col in lv1_outputs.columns]
        
        # print(f"[DEBUG] Displaying Lv1 results\n{lv1_protocol}\n{lv1_outputs}")
        return html.Div([
            dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                html.Strong("Lv1 Protocol Generated: "),
                f"{len(lv1_protocol)} transfer steps for {len(lv1_outputs)} assemblies"
            ], color="success", className="mb-3"),
            
            html.Div([
                html.H6([html.I(className="fas fa-list me-2"), "Protocol Steps"], className="mb-2 d-inline-block"),
                dbc.Button([
                    html.I(className="fas fa-download me-2"),
                    "Export CSV"
                ], id="export-lv1-protocol-btn", color="primary", size="sm", className="float-end mb-2")
            ], className="d-flex justify-content-between align-items-center"),
            dcc.Download(id="download-lv1-protocol"),
            dag.AgGrid(
                id='lv1-protocol-grid',
                rowData=lv1_protocol.to_dict('records'),
                columnDefs=[
                    {
                        'field': col,
                        'headerName': str(col).replace('_', '.'),  # Display with dots
                        'filter': True,
                        'sortable': True,
                        'resizable': True,
                        'editable': False,
                        'wrapText': True,
                        'autoHeight': True,
                        'flex': 1,
                        'minWidth': 120
                    } for col in lv1_protocol.columns
                ],
                defaultColDef={
                    'filter': True,
                    'sortable': True,
                    'resizable': True,
                    'minWidth': 120
                },
                dashGridOptions={
                    'pagination': True,
                    'paginationPageSize': 15,
                    'paginationPageSizeSelector': [10, 15, 25, 50],
                    'enableCellTextSelection': True,
                    'ensureDomOrder': True,
                    'rowSelection': 'multiple',
                    'animateRows': True,
                    'defaultCsvExportParams': {'fileName': 'lv1_protocol.csv'},
                    'popupParent': 'body'
                },
                className='ag-theme-alpine-dark',
                style={'height': '500px', 'width': '100%', 'marginBottom': '20px'},
                csvExportParams={'fileName': 'lv1_protocol.csv'},
                enableEnterpriseModules=False
            ),
            
            html.Hr(className="my-4"),
            
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-flask me-2"), "Output Assemblies",
                     html.I(className="fas fa-chevron-down ms-2", id="lv1-outputs-icon")],
                    id="lv1-outputs-toggle",
                    color="secondary",
                    className="mb-2",
                    n_clicks=0,
                    style={"textAlign": "left"}
                ),
                dbc.Button([
                    html.I(className="fas fa-download me-2"),
                    "Export CSV"
                ], id="export-lv1-outputs-btn", color="primary", size="sm", className="float-end mb-2")
            ], className="d-flex justify-content-between align-items-center"),
            dcc.Download(id="download-lv1-outputs"),
            dbc.Collapse(
                dag.AgGrid(
                    id='lv1-outputs-grid',
                    rowData=lv1_outputs.to_dict('records'),
                    columnDefs=[
                        {
                            'field': col,
                            'headerName': str(col).replace('_', '.'),
                            'filter': True,
                            'sortable': True,
                            'resizable': True,
                            'editable': False,
                            'wrapText': True,
                            'autoHeight': False,
                            'width': 150 if str(col).isdigit() else None,
                            'flex': 0 if str(col).isdigit() else 1,
                            'minWidth': 100
                        } for col in lv1_outputs.columns
                    ],
                    defaultColDef={
                        'filter': True,
                        'sortable': True,
                        'resizable': True,
                        'minWidth': 100
                    },
                    dashGridOptions={
                        'pagination': True,
                        'paginationPageSize': 10,
                        'paginationPageSizeSelector': [10, 20, 50],
                        'enableCellTextSelection': True,
                        'ensureDomOrder': True,
                        'rowSelection': 'multiple',
                        'animateRows': True,
                        'defaultCsvExportParams': {'fileName': 'lv1_outputs.csv'},
                        'popupParent': 'body'
                    },
                    className='ag-theme-alpine-dark',
                    style={'height': '400px', 'width': '100%', 'marginBottom': '20px'},
                    csvExportParams={'fileName': 'lv1_outputs.csv'},
                    enableEnterpriseModules=False
                ),
                id="lv1-outputs-collapse",
                is_open=False
            )
        ])
        
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error displaying results: {str(e)}"
        ], color="danger")

# Callback to display Lv2 results
@app.callback(
    Output('lv2-results-container', 'children'),
    [Input('lv2-protocol-data', 'data'),
     Input('lv2-outputs-data', 'data')]
)
def display_lv2_results(lv2_protocol_json, lv2_outputs_json):
    if not lv2_protocol_json:
        return dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "Lv2 protocol will be generated after Lv1 protocol is complete."
        ], color="info")
    
    try:
        lv2_protocol = pd.read_json(StringIO(lv2_protocol_json), orient='split')
        lv2_outputs = pd.read_json(StringIO(lv2_outputs_json), orient='split')
        
        # Rename columns with dots to underscores for AG Grid compatibility
        lv2_protocol.columns = [str(col).replace('.', '_') for col in lv2_protocol.columns]
        lv2_outputs.columns = [str(col).replace('.', '_') for col in lv2_outputs.columns]
        
        return html.Div([
            dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                html.Strong("Lv2 Protocol Generated: "),
                f"{len(lv2_protocol)} transfer steps for {len(lv2_outputs)} final assemblies"
            ], color="success", className="mb-3"),
            
            html.Div([
                html.H6([html.I(className="fas fa-list me-2"), "Protocol Steps"], className="mb-2 d-inline-block"),
                dbc.Button([
                    html.I(className="fas fa-download me-2"),
                    "Export CSV"
                ], id="export-lv2-protocol-btn", color="primary", size="sm", className="float-end mb-2")
            ], className="d-flex justify-content-between align-items-center"),
            dcc.Download(id="download-lv2-protocol"),
            dag.AgGrid(
                id='lv2-protocol-grid',
                rowData=lv2_protocol.to_dict('records'),
                columnDefs=[
                    {
                        'field': col,
                        'headerName': str(col).replace('_', '.'),  # Display with dots
                        'filter': True,
                        'sortable': True,
                        'resizable': True,
                        'editable': False,
                        'wrapText': True,
                        'autoHeight': True,
                        'flex': 1,
                        'minWidth': 120
                    } for col in lv2_protocol.columns
                ],
                defaultColDef={
                    'filter': True,
                    'sortable': True,
                    'resizable': True,
                    'minWidth': 120
                },
                dashGridOptions={
                    'pagination': True,
                    'paginationPageSize': 15,
                    'paginationPageSizeSelector': [10, 15, 25, 50],
                    'enableCellTextSelection': True,
                    'ensureDomOrder': True,
                    'rowSelection': 'multiple',
                    'animateRows': True,
                    'defaultCsvExportParams': {'fileName': 'lv2_protocol.csv'},
                    'popupParent': 'body'
                },
                className='ag-theme-alpine-dark',
                style={'height': '500px', 'width': '100%', 'marginBottom': '20px'},
                csvExportParams={'fileName': 'lv2_protocol.csv'},
                enableEnterpriseModules=False
            ),
            
            html.Hr(className="my-4"),
            
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-dna me-2"), "Final Assemblies",
                     html.I(className="fas fa-chevron-down ms-2", id="lv2-outputs-icon")],
                    id="lv2-outputs-toggle",
                    color="secondary",
                    className="mb-2",
                    n_clicks=0,
                    style={"textAlign": "left"}
                ),
                dbc.Button([
                    html.I(className="fas fa-download me-2"),
                    "Export CSV"
                ], id="export-lv2-outputs-btn", color="primary", size="sm", className="float-end mb-2")
            ], className="d-flex justify-content-between align-items-center"),
            dcc.Download(id="download-lv2-outputs"),
            dbc.Collapse(
                dag.AgGrid(
                    id='lv2-outputs-grid',
                    rowData=lv2_outputs.to_dict('records'),
                    columnDefs=[
                        {
                            'field': col,
                            'headerName': str(col).replace('_', '.'),
                            'filter': True,
                            'sortable': True,
                            'resizable': True,
                            'editable': False,
                            'wrapText': True,
                            'autoHeight': False,
                            'width': 150 if str(col).isdigit() else None,
                            'flex': 0 if str(col).isdigit() else 1,
                            'minWidth': 100
                        } for col in lv2_outputs.columns
                    ],
                    defaultColDef={
                        'filter': True,
                        'sortable': True,
                        'resizable': True,
                        'minWidth': 100
                    },
                    dashGridOptions={
                        'pagination': True,
                        'paginationPageSize': 10,
                        'paginationPageSizeSelector': [10, 20, 50],
                        'enableCellTextSelection': True,
                        'ensureDomOrder': True,
                        'rowSelection': 'multiple',
                        'animateRows': True,
                        'defaultCsvExportParams': {'fileName': 'lv2_outputs.csv'},
                        'popupParent': 'body'
                    },
                    className='ag-theme-alpine-dark',
                    style={'height': '400px', 'width': '100%', 'marginBottom': '20px'},
                    csvExportParams={'fileName': 'lv2_outputs.csv'},
                    enableEnterpriseModules=False
                ),
                id="lv2-outputs-collapse",
                is_open=False
            )
        ])
        
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error displaying results: {str(e)}"
        ], color="danger")

# Callback for OT2 conversion
@app.callback(
    Output('ot2-conversion-container', 'children'),
    [Input('convert-option', 'value'),
     Input('lv1-protocol-data', 'data'),
     Input('lv2-protocol-data', 'data')],
    [State('sources-data', 'data')]
)
def convert_to_ot2(convert_option, lv1_protocol_json, lv2_protocol_json, sources_json):
    if convert_option != 'ot2' or not lv1_protocol_json:
        return html.Div()
    
    try:
        lv1_protocol = pd.read_json(lv1_protocol_json, orient='split')
        sources = pd.read_json(sources_json, orient='split')
        
        # Generate OT2 scripts
        sheet_names = sources['plate'].unique().tolist()
        
        # Lv1 OT2 Script
        metadata_lv1 = "'protocolName': 'Lv1 Assembly Protocol',\\n'robotType': 'OT-2'"
        requirements_lv1 = '"robotType": "OT-2", "apiLevel": "2.17"'
        plate_posit_lv1, _ = create_ot2_labware_settings(sheet_names, ['Lv1_destination_1'], 'lv1')
        ot2_script_lv1 = protocol_to_ot2_script(lv1_protocol, metadata_lv1, requirements_lv1, plate_posit_lv1)
        
        result = [
            dbc.Card([
                dbc.CardHeader([
                    html.H6([
                        html.I(className="fas fa-robot me-2"),
                        "Level 1 OT2 Python Script"
                    ], className="mb-0 text-white")
                ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
                dbc.CardBody([
                    dbc.Textarea(
                        value=ot2_script_lv1,
                        style={'fontFamily': 'monospace', 'fontSize': '12px', 'height': '400px'},
                        className="mb-2"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-download me-2"),
                        "Download Lv1 Script"
                    ], id='download-lv1-ot2', color="primary")
                ])
            ], className="shadow-sm mb-3", style={"border": "none", "border-radius": "15px"})
        ]
        
        # Lv2 OT2 Script (if available)
        if lv2_protocol_json:
            lv2_protocol = pd.read_json(lv2_protocol_json, orient='split')
            metadata_lv2 = "'protocolName': 'Lv2 Assembly Protocol',\\n'robotType': 'OT-2'"
            requirements_lv2 = '"robotType": "OT-2", "apiLevel": "2.17"'
            plate_posit_lv2, _ = create_ot2_labware_settings(sheet_names, ['Lv2_destination_1'], 'lv2')
            ot2_script_lv2 = protocol_to_ot2_script(lv2_protocol, metadata_lv2, requirements_lv2, plate_posit_lv2)
            
            result.append(
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-robot me-2"),
                            "Level 2 OT2 Python Script"
                        ], className="mb-0 text-white")
                    ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
                    dbc.CardBody([
                        dbc.Textarea(
                            value=ot2_script_lv2,
                            style={'fontFamily': 'monospace', 'fontSize': '12px', 'height': '400px'},
                            className="mb-2"
                        ),
                        dbc.Button([
                            html.I(className="fas fa-download me-2"),
                            "Download Lv2 Script"
                        ], id='download-lv2-ot2', color="primary")
                    ])
                ], className="shadow-sm", style={"border": "none", "border-radius": "15px"})
            )
        
        return result
        
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error generating OT2 script: {str(e)}"
        ], color="danger")

# Callbacks for collapsible Output Assemblies sections
@app.callback(
    [Output("lv1-outputs-collapse", "is_open"),
     Output("lv1-outputs-icon", "className")],
    [Input("lv1-outputs-toggle", "n_clicks")],
    [State("lv1-outputs-collapse", "is_open")]
)
def toggle_lv1_outputs(n_clicks, is_open):
    if n_clicks:
        return not is_open, "fas fa-chevron-up ms-2" if not is_open else "fas fa-chevron-down ms-2"
    return is_open, "fas fa-chevron-down ms-2"

@app.callback(
    [Output("lv2-outputs-collapse", "is_open"),
     Output("lv2-outputs-icon", "className")],
    [Input("lv2-outputs-toggle", "n_clicks")],
    [State("lv2-outputs-collapse", "is_open")]
)
def toggle_lv2_outputs(n_clicks, is_open):
    if n_clicks:
        return not is_open, "fas fa-chevron-up ms-2" if not is_open else "fas fa-chevron-down ms-2"
    return is_open, "fas fa-chevron-down ms-2"

# Callbacks for CSV export buttons
@app.callback(
    Output("download-lv1-protocol", "data"),
    Input("export-lv1-protocol-btn", "n_clicks"),
    State("lv1-protocol-data", "data"),
    prevent_initial_call=True
)
def export_lv1_protocol(n_clicks, lv1_protocol_json):
    if lv1_protocol_json:
        lv1_protocol = pd.read_json(StringIO(lv1_protocol_json), orient='split')
        # Restore dots in column names for export
        lv1_protocol.columns = [str(col).replace('_', '.') for col in lv1_protocol.columns]
        return dcc.send_data_frame(lv1_protocol.to_csv, "lv1_protocol.csv", index=False)
    return None

@app.callback(
    Output("download-lv1-outputs", "data"),
    Input("export-lv1-outputs-btn", "n_clicks"),
    State("lv1-outputs-data", "data"),
    prevent_initial_call=True
)
def export_lv1_outputs(n_clicks, lv1_outputs_json):
    if lv1_outputs_json:
        lv1_outputs = pd.read_json(StringIO(lv1_outputs_json), orient='split')
        # Restore dots in column names for export
        lv1_outputs.columns = [str(col).replace('_', '.') for col in lv1_outputs.columns]
        return dcc.send_data_frame(lv1_outputs.to_csv, "lv1_outputs.csv", index=False)
    return None

@app.callback(
    Output("download-lv2-protocol", "data"),
    Input("export-lv2-protocol-btn", "n_clicks"),
    State("lv2-protocol-data", "data"),
    prevent_initial_call=True
)
def export_lv2_protocol(n_clicks, lv2_protocol_json):
    if lv2_protocol_json:
        lv2_protocol = pd.read_json(StringIO(lv2_protocol_json), orient='split')
        # Restore dots in column names for export
        lv2_protocol.columns = [str(col).replace('_', '.') for col in lv2_protocol.columns]
        return dcc.send_data_frame(lv2_protocol.to_csv, "lv2_protocol.csv", index=False)
    return None

@app.callback(
    Output("download-lv2-outputs", "data"),
    Input("export-lv2-outputs-btn", "n_clicks"),
    State("lv2-outputs-data", "data"),
    prevent_initial_call=True
)
def export_lv2_outputs(n_clicks, lv2_outputs_json):
    if lv2_outputs_json:
        lv2_outputs = pd.read_json(StringIO(lv2_outputs_json), orient='split')
        # Restore dots in column names for export
        lv2_outputs.columns = [str(col).replace('_', '.') for col in lv2_outputs.columns]
        return dcc.send_data_frame(lv2_outputs.to_csv, "lv2_outputs.csv", index=False)
    return None

if __name__ == '__main__':
    app.run(debug=True, port=8050)
