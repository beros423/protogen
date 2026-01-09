from dash import dcc, html, Input, Output, State, callback_context, dash_table, ALL, MATCH
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import dash
import pandas as pd
import json
from itertools import product
from io import StringIO, BytesIO
import base64

# Import core functions from main module
from main import find_source_well

# Import generate_janus_protocol separately (will be replaced with fixed version)
def generate_janus_protocol(sources_janus, designs, destination_name, sources, plate_type=96):
    """Generate Janus protocol without streamlit dependencies"""
    protocol_rows = pd.DataFrame(columns=["Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"])
    output_rows = pd.DataFrame(columns=["name","plate","well","volume","note"])
    volume_error = False
    
    # plate_type에 따른 row 길이 설정
    if plate_type == 96:
        row_len = 12
    elif plate_type == 384:
        row_len = 24
    else:
        raise ValueError("plate_type must be either 96 or 384")

    for index, design in enumerate(designs):
        if volume_error:
            protocol_rows, output_rows = None, None
            break
        
        # set target destination well
        dest_list = ["A","B","C","D","E","F","G","H"]
        dest_row = int(index / row_len)
        destination = f"{dest_list[dest_row]}{index + 1 - row_len*(dest_row)}"
        protocol_row = {
            "Component": f"{destination_name}_{index+1}",
            "Asp.Rack": "",
            "Asp.Posi": "",
            "Dsp.Rack": destination_name,
            "Dsp.Posi": destination,
            "Volume": 0,
            "Note": ""
        }
        output_row = {
            "name":f"{destination_name}_{index+1}",
            "plate":destination_name,
            "well":destination,
            "volume":0,
            "note":""
        }
        # Extracting data from sources with designs
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']

            try:
                plate, well = find_source_well(sources_janus, name, vol)
            except ValueError as e:
                total_need = 0
                for design in designs:
                    for k, item in enumerate(design):
                        if item['name'] == name:
                            total_need += item['volume']
                total_have = sources.loc[sources['name'] == name, 'volume'].sum()
                # Raise error with detailed message instead of using streamlit
                raise ValueError(f"Not enough volume for '{name}': have {total_have}ul, need {total_need}ul")

            protocol_row["Asp.Rack"] = plate
            protocol_row["Asp.Posi"] = well
            protocol_row["Note"] = name
            protocol_row["Volume"] = vol
            
            output_row['note'] += f"{name}/"
            output_row['volume'] += vol
            output_row[f'part_{k}'] = name  # Use string key instead of numeric

            protocol_rows = pd.concat([protocol_rows, pd.DataFrame([protocol_row])])
        output_row['note'] = output_row['note'][:-1]
        output_rows = pd.concat([output_rows,  pd.DataFrame([output_row])])

    return protocol_rows, output_rows

# Initialize Dash app with Bootstrap theme and Font Awesome
external_stylesheets = [
    dbc.themes.DARKLY,
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "ProtoGen Universal - Assembly Design Tool"

# Helper functions
def load_design_from_csv(contents, filename):
    """Load assembly design from CSV file."""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(BytesIO(decoded))
        
        # Extract part types from header (columns)
        part_types = [col for col in df.columns if col != 'Group']
        
        # Process each row as one assembly design
        assemblies = []
        
        for row_idx, row in df.iterrows():
            assembly_parts = {}
            
            for part_type in part_types:
                cell_value = str(row.get(part_type, '')).strip()
                if cell_value and cell_value != 'nan':
                    parts_list = [part.strip() for part in cell_value.split(';') if part.strip()]
                    assembly_parts[part_type] = parts_list
                else:
                    assembly_parts[part_type] = []
            
            if any(assembly_parts.values()):
                assemblies.append(assembly_parts)
        
        # Return in the expected format
        if assemblies:
            return [{
                'group_name': 'Loaded_Design',
                'assemblies': assemblies,
                'part_types': part_types
            }]
        return None
        
    except Exception as e:
        print(f"Error loading design from CSV: {str(e)}")
        return None

def load_design_from_json(contents, filename):
    """Load assembly design from JSON file."""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data = json.loads(decoded)
        return [data] if isinstance(data, dict) else data
    except Exception as e:
        print(f"Error loading design from JSON: {str(e)}")
        return None

def create_design_template_files():
    """Create template files for design import."""
    csv_template = """Promoter,CDS,Terminator,Backbone
pTrc;pLac,gfp,rrnB_T1,pUC19
pBAD,rfp;bfp,rrnB_T2,pBR322
pTet,yfp,dbl_term,pBR322"""
    
    json_template = {
        "group_name": "Universal_Design",
        "assemblies": [
            {
                "Promoter": ["pTrc", "pLac"],
                "CDS": ["gfp"],
                "Terminator": ["rrnB_T1"],
                "Backbone": ["pUC19"]
            },
            {
                "Promoter": ["pBAD"],
                "CDS": ["rfp", "bfp"],
                "Terminator": ["rrnB_T2"],
                "Backbone": ["pBR322"]
            }
        ],
        "part_types": ["Promoter", "CDS", "Terminator", "Backbone"]
    }
    
    return csv_template, json.dumps(json_template, indent=2)

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
    """Step 2: Design Configuration"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-cog me-3", style={"color": "#667eea"}),
                        "Step 2: Assembly Design"
                    ], className="mb-2"),
                    html.P("Configure assembly design and part volumes.", 
                           className="text-muted")
                ])
            ])
        ], className="mb-4"),
        
        # Design File Upload
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-file-import me-2"),
                    "Load Assembly Design from File (Optional)"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
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
        
        # Assembly Configuration
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-layer-group me-2"),
                    "Assembly Configuration"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Number of Assemblies", className="fw-bold mb-2"),
                        dbc.Input(
                            id="num-assemblies", 
                            type="number", 
                            value=3, 
                            min=1, 
                            step=1,
                            className="form-control-lg"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Parts per Assembly", className="fw-bold mb-2"),
                        dbc.Input(
                            id="num-parts", 
                            type="number", 
                            value=4, 
                            min=1, 
                            step=1,
                            className="form-control-lg"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Repeats per Assembly", className="fw-bold mb-2"),
                        dbc.Input(
                            id="num-repeats", 
                            type="number", 
                            value=1, 
                            min=1, 
                            step=1,
                            className="form-control-lg"
                        )
                    ], md=4)
                ])
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # Part Types and Volumes
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-dna me-2"),
                    "Part Types & Volumes"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                html.Div(id='part-types-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # Assembly Design Matrix
        html.Div(id='assembly-design-container')
    ], fluid=True)

def create_step3_layout():
    """Step 3: Common Parts"""
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
        
        # Commons
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-layer-group me-2"),
                    "Common Parts"
                ], className="mb-0 d-inline text-white"),
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-plus me-1"),
                        "Add"
                    ], id="btn-commons-add", color="light", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-minus me-1"),
                        "Remove"
                    ], id="btn-commons-remove", color="light", size="sm", outline=True)
                ], size="sm", className="float-end")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "These parts will be included in every assembly."
                ], color="info", className="mb-3"),
                html.Div(id='commons-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        html.Div(id='total-volume-display', className="mb-4")
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
        
        # Output Configuration
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-vial me-2"),
                    "Output Configuration"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Destination Plate Name", className="fw-bold mb-2"),
                        dbc.Input(
                            id='dest-plate-name',
                            type="text",
                            value="dest_01",
                            className="form-control-lg"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Destination Plate Type", className="fw-bold mb-2"),
                        dcc.Dropdown(
                            id='dest-plate-type',
                            options=[
                                {'label': '96-well plate', 'value': 96},
                                {'label': '384-well plate', 'value': 384}
                            ],
                            value=96,
                            className="mb-3",
                            style={'color': 'black'}
                        )
                    ], md=6)
                ])
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"}),
        
        # Results
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-robot me-2"),
                    "Generated Protocol"
                ], className="mb-0 text-white")
            ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
            dbc.CardBody([
                html.Div(id='protocol-results-container')
            ])
        ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"})
    ], fluid=True)

# Main Layout
app.layout = html.Div([
    # Stores
    dcc.Store(id='sources-data'),
    dcc.Store(id='design-data'),
    dcc.Store(id='loaded-design-data'),
    dcc.Store(id='commons-count', data=1),
    dcc.Store(id='protocol-data'),
    dcc.Store(id='outputs-data'),
    dcc.Store(id='part-selections-data'),
    
    # Header
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1([
                        html.I(className="fas fa-dna me-3", style={"color": "#667eea"}),
                        "ProtoGen Universal - Assembly Design Tool"
                    ], className="text-center my-4", style={"font-weight": "700"}),
                    html.P([
                        html.I(className="fas fa-info-circle me-2"),
                        "Universal assembly design for synthetic biology projects"
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
                                        html.Span("Commons")
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
        {'display': 'block'},
        {'display': 'none'},
        {'display': 'none'},
        {'display': 'none'}
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
    
    return styles + active

# Sources upload callback
@app.callback(
    [Output('sources-data', 'data'),
     Output('source-upload-status', 'children')],
    Input('upload-sources', 'contents'),
    State('upload-sources', 'filename')
)
def upload_sources(contents, filename):
    if contents is None:
        return None, ""
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(BytesIO(decoded))
        
        # Validate required columns
        required_cols = ['type', 'name', 'plate', 'well', 'volume', 'note']
        if not all(col in df.columns for col in required_cols):
            return None, dbc.Alert("❌ CSV must contain columns: type, name, plate, well, volume, note", 
                                  color="danger")
        
        sources = df[required_cols].to_dict('records')
        
        return sources, dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"✅ Successfully loaded {len(sources)} source entries from {filename}"
        ], color="success")
        
    except Exception as e:
        return None, dbc.Alert(f"❌ Error loading file: {str(e)}", color="danger")

# Source preview callback
@app.callback(
    Output('source-preview', 'children'),
    Input('sources-data', 'data')
)
def update_source_preview(sources_data):
    if not sources_data:
        return dbc.Alert("No source data loaded yet.", color="info", className="text-center")
    
    df = pd.DataFrame(sources_data)
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-table me-2"),
                "Source Plate Preview"
            ], className="mb-0 text-white")
        ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
        dbc.CardBody([
            dag.AgGrid(
                id='source-grid',
                rowData=df.to_dict('records'),
                columnDefs=[
                    {
                        'field': str(col),
                        'headerName': str(col),
                        'filter': True,
                        'sortable': True,
                        'resizable': True,
                        'editable': False,
                        'wrapText': True,
                        'autoHeight': True,
                        'flex': 1 if col in ['name', 'plate', 'type'] else 0,
                        'minWidth': 100
                    } for col in df.columns
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
    ], className="shadow-sm", style={"border": "none", "border-radius": "15px"})

# Template download callbacks
@app.callback(
    Output('download-csv-template', 'data'),
    Input('btn-csv-template', 'n_clicks'),
    prevent_initial_call=True
)
def download_csv_template(n_clicks):
    csv_template, _ = create_design_template_files()
    return dict(content=csv_template, filename="assembly_design_template.csv")

@app.callback(
    Output('download-json-template', 'data'),
    Input('btn-json-template', 'n_clicks'),
    prevent_initial_call=True
)
def download_json_template(n_clicks):
    _, json_template = create_design_template_files()
    return dict(content=json_template, filename="assembly_design_template.json")

# Design file upload callback
@app.callback(
    [Output('loaded-design-data', 'data'),
     Output('design-upload-status', 'children'),
     Output('num-assemblies', 'value'),
     Output('num-parts', 'value')],
    Input('upload-design', 'contents'),
    State('upload-design', 'filename')
)
def upload_design(contents, filename):
    if contents is None:
        return None, "", dash.no_update, dash.no_update
    
    try:
        if filename.endswith('.csv'):
            loaded_data = load_design_from_csv(contents, filename)
        elif filename.endswith('.json'):
            loaded_data = load_design_from_json(contents, filename)
        else:
            return None, dbc.Alert("❌ Unsupported file format", color="danger"), dash.no_update, dash.no_update
        
        if loaded_data:
            num_assemblies = len(loaded_data[0]['assemblies'])
            num_parts = len(loaded_data[0]['part_types'])
            
            return loaded_data, dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"✅ Loaded design with {num_assemblies} assemblies and {num_parts} part types"
            ], color="success"), num_assemblies, num_parts
        else:
            return None, dbc.Alert("❌ Failed to load design", color="danger"), dash.no_update, dash.no_update
            
    except Exception as e:
        return None, dbc.Alert(f"❌ Error: {str(e)}", color="danger"), dash.no_update, dash.no_update

# Part types container callback
@app.callback(
    Output('part-types-container', 'children'),
    [Input('num-parts', 'value'),
     Input('sources-data', 'data'),
     Input('loaded-design-data', 'data')]
)
def update_part_types(num_parts, sources_data, loaded_design):
    if not sources_data or not num_parts:
        return html.P("Please load source data first.", className="text-muted")
    
    df = pd.DataFrame(sources_data)
    available_types = df['type'].unique().tolist()
    
    part_inputs = []
    
    for i in range(num_parts):
        # Get default type from loaded design if available
        default_type = available_types[0]
        if loaded_design and i < len(loaded_design[0]['part_types']):
            loaded_type = loaded_design[0]['part_types'][i]
            if loaded_type in available_types:
                default_type = loaded_type
        
        part_inputs.append(
            dbc.Row([
                dbc.Col([
                    html.Label(f"Part {i+1} Type", className="fw-bold mb-2"),
                    dcc.Dropdown(
                        id={'type': 'part-type', 'index': i},
                        options=[{'label': t, 'value': t} for t in available_types],
                        value=default_type,
                        style={'color': 'black'}
                    )
                ], md=8),
                dbc.Col([
                    html.Label("Volume (μl)", className="fw-bold mb-2"),
                    dbc.Input(
                        id={'type': 'part-volume', 'index': i},
                        type="number",
                        value=1.0,
                        step=0.1,
                        min=0
                    )
                ], md=4)
            ], className="mb-3")
        )
    
    return html.Div(part_inputs)

# Assembly design matrix callback
@app.callback(
    Output('assembly-design-container', 'children'),
    [Input('num-assemblies', 'value'),
     Input({'type': 'part-type', 'index': ALL}, 'value'),
     Input('sources-data', 'data'),
     Input('loaded-design-data', 'data')]
)
def update_assembly_design(num_assemblies, part_types, sources_data, loaded_design):
    if not sources_data or not num_assemblies or not part_types:
        return ""
    
    df = pd.DataFrame(sources_data)
    
    rows = []
    for assembly_idx in range(num_assemblies):
        cols = []
        for part_idx, part_type in enumerate(part_types):
            if not part_type:
                continue
                
            items = df[df['type'] == part_type]['name'].unique().tolist()
            
            # Get default selection from loaded design
            default_items = []
            if loaded_design and assembly_idx < len(loaded_design[0]['assemblies']):
                assembly_data = loaded_design[0]['assemblies'][assembly_idx]
                if part_type in assembly_data:
                    default_items = [item for item in assembly_data[part_type] if item in items]
            
            cols.append(
                dbc.Col([
                    html.Label(part_type, className="text-muted small"),
                    dcc.Dropdown(
                        id={'type': 'assembly-part', 'assembly': assembly_idx, 'part': part_idx},
                        options=[{'label': item, 'value': item} for item in items],
                        value=default_items,
                        multi=True,
                        style={'color': 'black'}
                    )
                ])
            )
        
        rows.append(
            dbc.Card([
                dbc.CardHeader(f"Assembly {assembly_idx + 1}"),
                dbc.CardBody([
                    dbc.Row(cols, className="g-2")
                ])
            ], className="mb-3", style={"border-radius": "10px"})
        )
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-project-diagram me-2"),
                "Assembly Design Matrix"
            ], className="mb-0 text-white")
        ], style={"background": "linear-gradient(135deg, #4a5568 0%, #2d3748 100%)", "border": "none"}),
        dbc.CardBody(rows)
    ], className="shadow-sm mb-4", style={"border": "none", "border-radius": "15px"})

# Commons count callback
@app.callback(
    Output('commons-count', 'data'),
    [Input('btn-commons-add', 'n_clicks'),
     Input('btn-commons-remove', 'n_clicks')],
    State('commons-count', 'data'),
    prevent_initial_call=True
)
def update_commons_count(add_clicks, remove_clicks, current_count):
    ctx = callback_context
    if not ctx.triggered:
        return current_count
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-commons-add':
        return current_count + 1
    elif button_id == 'btn-commons-remove' and current_count > 0:
        return max(0, current_count - 1)
    
    return current_count

# Commons container callback
@app.callback(
    Output('commons-container', 'children'),
    [Input('commons-count', 'data'),
     Input('sources-data', 'data')]
)
def update_commons_fields(count, sources_data):
    if not sources_data or count == 0:
        return html.P("No common parts added.", className="text-muted")
    
    df = pd.DataFrame(sources_data)
    types = df['type'].unique().tolist()
    
    fields = []
    for i in range(count):
        fields.append(
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id={'type': 'common-type', 'index': i},
                        options=[{'label': t, 'value': t} for t in types],
                        placeholder="Select type",
                        style={'color': 'black'}
                    )
                ], md=4),
                dbc.Col([
                    dcc.Dropdown(
                        id={'type': 'common-name', 'index': i},
                        placeholder="Select part",
                        style={'color': 'black'}
                    )
                ], md=5),
                dbc.Col([
                    dbc.Input(
                        id={'type': 'common-volume', 'index': i},
                        type="number",
                        value=1.0,
                        step=0.1,
                        min=0,
                        placeholder="Volume"
                    )
                ], md=3)
            ], className="mb-2")
        )
    
    return html.Div(fields)

# Update common part names based on type selection
@app.callback(
    Output({'type': 'common-name', 'index': MATCH}, 'options'),
    Input({'type': 'common-type', 'index': MATCH}, 'value'),
    State('sources-data', 'data')
)
def update_common_names(selected_type, sources_data):
    if not selected_type or not sources_data:
        return []
    
    df = pd.DataFrame(sources_data)
    names = df[df['type'] == selected_type]['name'].unique().tolist()
    return [{'label': name, 'value': name} for name in names]

# Total volume calculation
@app.callback(
    Output('total-volume-display', 'children'),
    [Input({'type': 'part-volume', 'index': ALL}, 'value'),
     Input({'type': 'common-volume', 'index': ALL}, 'value')]
)
def calculate_total_volume(part_volumes, common_volumes):
    total = sum(v for v in part_volumes if v) + sum(v for v in common_volumes if v)
    
    return dbc.Alert([
        html.I(className="fas fa-flask me-2"),
        f"Total volume per assembly: {total:.2f} μl"
    ], color="info", className="text-center")

# Generate protocol callback
@app.callback(
    [Output('protocol-data', 'data'),
     Output('outputs-data', 'data'),
     Output('protocol-results-container', 'children')],
    Input('nav-results', 'n_clicks'),
    [State('sources-data', 'data'),
     State('num-assemblies', 'value'),
     State('num-repeats', 'value'),
     State({'type': 'part-type', 'index': ALL}, 'value'),
     State({'type': 'part-volume', 'index': ALL}, 'value'),
     State({'type': 'assembly-part', 'assembly': ALL, 'part': ALL}, 'value'),
     State({'type': 'common-type', 'index': ALL}, 'value'),
     State({'type': 'common-name', 'index': ALL}, 'value'),
     State({'type': 'common-volume', 'index': ALL}, 'value'),
     State('dest-plate-name', 'value'),
     State('dest-plate-type', 'value')],
    prevent_initial_call=True
)
def generate_protocol(nav_clicks, sources_data, num_assemblies, num_repeats,
                     part_types, part_volumes, assembly_selections,
                     common_types, common_names, common_volumes,
                     dest_plate_name, dest_plate_type):
    
    if not sources_data:
        return None, None, dbc.Alert("No source data available", color="warning")
    
    try:
        # Build designs list
        designs = []
        sources_df = pd.DataFrame(sources_data)
        
        # Build commons list
        commons = []
        for ctype, cname, cvol in zip(common_types, common_names, common_volumes):
            if ctype and cname and cvol:
                commons.append({'name': cname, 'volume': cvol})
        
        # Process each assembly
        for assembly_idx in range(num_assemblies):
            assembly_parts = {}
            
            for part_idx, (part_type, part_vol) in enumerate(zip(part_types, part_volumes)):
                # Find the selections for this assembly and part
                matching_selections = [
                    sel for sel in assembly_selections 
                    if isinstance(sel, list) and len(sel) > 0
                ]
                
                if part_idx < len(matching_selections):
                    selected_items = matching_selections[part_idx] if isinstance(matching_selections[part_idx], list) else [matching_selections[part_idx]]
                else:
                    selected_items = []
                
                if selected_items and selected_items != [""]:
                    assembly_parts[part_type] = [(item, part_vol) for item in selected_items if item]
            
            # Generate combinations
            if assembly_parts:
                part_types_order = list(assembly_parts.keys())
                part_combinations = list(product(*[assembly_parts[pt] for pt in part_types_order]))
                
                for combo in part_combinations:
                    design = []
                    for item, vol in combo:
                        if item:
                            design.append({'name': item, 'volume': vol})
                    design = design + commons
                    
                    for _ in range(num_repeats):
                        designs.append(design)
        
        if not designs:
            return None, None, dbc.Alert("No valid designs generated", color="warning")
        
        # Generate Janus protocol
        sources_janus = sources_df.copy()
        protocol, lv1_outputs = generate_janus_protocol(
            sources_janus, designs, dest_plate_name, sources_df, dest_plate_type
        )
        
        # Rename columns with dots to underscores for AG Grid compatibility
        protocol.columns = [str(col).replace('.', '_') for col in protocol.columns]
        lv1_outputs.columns = [str(col).replace('.', '_') for col in lv1_outputs.columns]
        
        # Convert to JSON for storage
        protocol_json = protocol.to_json(orient='records')
        outputs_json = lv1_outputs.to_json(orient='records')
        
        # Create results display
        results = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-list me-2"),
                            "Protocol Table"
                        ], className="mb-2 d-inline-block"),
                        dbc.Button([
                            html.I(className="fas fa-download me-2"),
                            "Export CSV"
                        ], id="export-protocol-btn", color="primary", size="sm", className="float-end mb-2")
                    ], className="d-flex justify-content-between align-items-center"),
                    dcc.Download(id="download-protocol"),
                    dag.AgGrid(
                        id='protocol-grid',
                        rowData=protocol.to_dict('records'),
                        columnDefs=[
                            {
                                'field': str(col),
                                'headerName': str(col).replace('_', '.'),
                                'filter': True,
                                'sortable': True,
                                'resizable': True,
                                'editable': False,
                                'wrapText': True,
                                'autoHeight': True,
                                'flex': 1,
                                'minWidth': 120
                            } for col in protocol.columns
                        ],
                        defaultColDef={
                            'filter': True,
                            'sortable': True,
                            'resizable': True,
                            'minWidth': 100
                        },
                        dashGridOptions={
                            'pagination': False,
                            # 'paginationPageSize': 20,
                            # 'paginationPageSizeSelector': [10, 20, 50, 100],
                            'enableCellTextSelection': True,
                            'ensureDomOrder': True,
                            'rowSelection': 'multiple',
                            'animateRows': True, 
                            'defaultCsvExportParams': {'fileName': 'protocol.csv'},
                            'popupParent': 'body'
                        },
                        csvExportParams={'fileName': 'protocol.csv'},
                        className='ag-theme-alpine-dark',
                        style={'height': '600px', 'width': '100%'}
                    )
                ])
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-vials me-2"),
                            "Output Plate"
                        ], className="mb-2 d-inline-block"),
                        dbc.Button([
                            html.I(className="fas fa-download me-2"),
                            "Export CSV"
                        ], id="export-outputs-btn", color="primary", size="sm", className="float-end mb-2")
                    ], className="d-flex justify-content-between align-items-center"),
                    dcc.Download(id="download-outputs"),
                    dag.AgGrid(
                        id='outputs-grid',
                        rowData=lv1_outputs.to_dict('records'),
                        columnDefs=[
                            {
                                'field': str(col),
                                'headerName': str(col).replace('_', '.'),
                                'filter': True,
                                'sortable': True,
                                'resizable': True,
                                'editable': False,
                                'wrapText': True,
                                'autoHeight': True,
                                'flex': 1,
                                'minWidth': 120
                            } for col in lv1_outputs.columns
                        ],
                        defaultColDef={
                            'filter': True,
                            'sortable': True,
                            'resizable': True,
                            'minWidth': 100
                        },
                        dashGridOptions={
                            'pagination': False,
                            # 'paginationPageSize': 20,
                            # 'paginationPageSizeSelector': [10, 20, 50, 100],
                            # 'domLayout': 'autoHeight',
                            'ensureDomOrder': True,
                            'rowSelection': 'multiple',
                            'enableCellTextSelection': True
                        },
                        csvExportParams={'fileName': 'outputs.csv'},
                        className='ag-theme-alpine-dark',
                        style={'height': '600px', 'width': '100%'}
                    )
                ])
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-database me-2"),
                            "Updated Sources"
                        ], className="mb-2 d-inline-block"),
                        dbc.Button([
                            html.I(className="fas fa-download me-2"),
                            "Export CSV"
                        ], id="export-sources-btn", color="primary", size="sm", className="float-end mb-2")
                    ], className="d-flex justify-content-between align-items-center"),
                    dcc.Download(id="download-sources"),
                    dag.AgGrid(
                        id='updated-sources-grid',
                        rowData=sources_janus.to_dict('records'),
                        columnDefs=[
                            {
                                'field': str(col),
                                'headerName': str(col),
                                'filter': True,
                                'sortable': True,
                                'resizable': True,
                                'editable': False,
                                'wrapText': True,
                                'flex': 1 if col in ['name', 'plate', 'type'] else 0,
                                'minWidth': 100
                            } for col in sources_janus.columns
                        ],
                        defaultColDef={
                            'filter': True,
                            'sortable': True,
                            'resizable': True,
                            'minWidth': 100
                        },
                        dashGridOptions={
                            'pagination': False,
                            # 'paginationPageSize': 20,
                            # 'paginationPageSizeSelector': [10, 20, 50, 100],
                            'enableCellTextSelection': True,
                            'ensureDomOrder': True,
                            'rowSelection': 'multiple',
                            'animateRows': True, 
                            'defaultCsvExportParams': {'fileName': 'sources.csv'},
                            'popupParent': 'body',
                        },
                        className='ag-theme-alpine-dark',
                        style={'height': '400px', 'width': '100%'}
                    )
                ])
            ])
        ], fluid=True)
        
        return protocol_json, outputs_json, results
        
    except Exception as e:
        return None, None, dbc.Alert(f"Error generating protocol: {str(e)}", color="danger")

# Callbacks for CSV export buttons
@app.callback(
    Output("download-protocol", "data"),
    Input("export-protocol-btn", "n_clicks"),
    State("protocol-data", "data"),
    prevent_initial_call=True
)
def export_protocol(n_clicks, protocol_json):
    if protocol_json:
        protocol = pd.read_json(StringIO(protocol_json), orient='records')
        # Restore dots in column names for export
        protocol.columns = [str(col).replace('_', '.') for col in protocol.columns]
        return dcc.send_data_frame(protocol.to_csv, "protocol.csv", index=False)
    return None

@app.callback(
    Output("download-outputs", "data"),
    Input("export-outputs-btn", "n_clicks"),
    State("outputs-data", "data"),
    prevent_initial_call=True
)
def export_outputs(n_clicks, outputs_json):
    if outputs_json:
        outputs = pd.read_json(StringIO(outputs_json), orient='records')
        # Restore dots in column names for export
        outputs.columns = [str(col).replace('_', '.') for col in outputs.columns]
        return dcc.send_data_frame(outputs.to_csv, "outputs.csv", index=False)
    return None

@app.callback(
    Output("download-sources", "data"),
    Input("export-sources-btn", "n_clicks"),
    State("sources-data", "data"),
    prevent_initial_call=True
)
def export_sources(n_clicks, sources_data):
    if sources_data:
        sources = pd.DataFrame(sources_data)
        return dcc.send_data_frame(sources.to_csv, "updated_sources.csv", index=False)
    return None

if __name__ == '__main__':
    app.run(debug=True, port=8051)
