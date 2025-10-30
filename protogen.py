import streamlit as st
import pandas as pd
from itertools import product
import math
import re
import json

# Streamlit 페이지 설정
st.set_page_config(layout="wide")

# Helper functions for UI components
def create_column_headers(columns, texts):
    """Create column headers with given texts."""
    cols = st.columns(columns)
    for i, text in enumerate(texts):
        with cols[i]:
            st.write(text)

def load_tu_design_from_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        design_data = []
        
        # Preserve original group order by using unique() instead of groupby
        # unique() maintains the order of first appearance
        unique_groups = df['Group'].unique()
        
        for group_name in unique_groups:
            # Filter rows for this group while preserving row order
            group_df = df[df['Group'] == group_name]
            
            group_design = {
                'group_name': group_name,
                'number_of_tu': len(group_df),
                'designs': []
            }
            
            # Each row is one TU design
            for _, row in group_df.iterrows():
                # Parse multiple selections (separated by semicolon)
                promoters = str(row.get('Promoter', '')).split(';') if pd.notna(row.get('Promoter')) else ['']
                cds_list = str(row.get('CDS', '')).split(';') if pd.notna(row.get('CDS')) else ['']
                terminators = str(row.get('Terminator', '')).split(';') if pd.notna(row.get('Terminator')) else ['']
                
                # Clean up whitespace
                promoters = [p.strip() for p in promoters if p.strip()]
                cds_list = [c.strip() for c in cds_list if c.strip()]
                terminators = [t.strip() for t in terminators if t.strip()]
                
                tu_design = {
                    'Promoter': promoters,
                    'CDS': cds_list,
                    'Terminator': terminators,
                    # 'Connector': ['(N)s|1']  # 기본 connector로 scar 사용
                }
                group_design['designs'].append(tu_design)
            
            design_data.append(group_design)
        
        return design_data
    except Exception as e:
        st.error(f"Error loading TU design from CSV: {str(e)}")
        return None

def create_input_row(columns, inputs_config):
    """Create a row of input fields based on configuration."""
    cols = st.columns(columns)
    results = []
    for i, config in enumerate(inputs_config):
        with cols[i]:
            if config['type'] == 'text':
                result = st.text_input(
                    label=config.get('label', ''),
                    value=config.get('value', ''),
                    key=config.get('key', ''),
                    label_visibility=config.get('label_visibility', 'visible'),
                    disabled=config.get('disabled', False)
                )
            elif config['type'] == 'number':
                result = st.number_input(
                    label=config.get('label', ''),
                    value=config.get('value', 0.0),
                    min_value=config.get('min_value', 0.0),
                    step=config.get('step', 0.1),
                    key=config.get('key', ''),
                    label_visibility=config.get('label_visibility', 'visible'),
                    disabled=config.get('disabled', False)
                )
            results.append(result)
    return results

def create_common_parts_section(title, session_key, default_name, default_plate, sources=None, default_volume=None):
    """Create a common parts input section."""
    col1, col2, col3 = st.columns([3, 1, 8])
    with col1: 
        st.write(f"### {title}")
    with col2: 
        if st.button('add', key=f"add_{session_key}"):
            st.session_state[session_key] += 1
    with col3: 
        if st.button('del', key=f"del_{session_key}") and st.session_state[session_key] > 0:
            st.session_state[session_key] -= 1
    
    # Headers
    create_column_headers([3,2,2,2], ["Part name", "Volume (ul)", "Stock plate", "Stock location"])
    
    common_parts = []
    for row in range(st.session_state[session_key]):
        col1, col2, col3, col4 = st.columns([3,2,2,2])
        with col1:
        # Check if name exists in sources first
            default_name_for_row = default_name
            selected_name = st.text_input(
                label="name", 
                value=default_name_for_row, 
                key=f'selectname_{session_key}_{row}', 
                label_visibility="collapsed"
            )
            name_exist = sources is not None and selected_name in sources['name'].values
            
            inputs_config = [
                {'type': 'text', 'label': 'name', 'value': default_name, 'key': f'dummy_{session_key}_{row}', 'label_visibility': 'collapsed'},
                {'type': 'number', 'label': 'vol', 'value': default_volume or (2.0 if 'lv1' in session_key else 10.0), 'step': 0.1, 'min_value': 0.0, 'key': f'volume_{session_key}_{row}', 'label_visibility': 'collapsed'},
                {'type': 'text', 'label': 'source plate', 'value': default_plate, 'key': f'common_source_plate_{session_key}_{row}', 'label_visibility': 'collapsed', 'disabled': name_exist},
                {'type': 'text', 'label': 'stock location', 'value': 'A1', 'key': f'common_stock_location_{session_key}_{row}', 'label_visibility': 'collapsed', 'disabled': name_exist}
            ]
        with col2:
            volume = st.number_input(
                label=inputs_config[1]['label'],
                value=inputs_config[1]['value'],
                min_value=inputs_config[1]['min_value'],
                step=inputs_config[1]['step'],
                key=inputs_config[1]['key'],
                label_visibility=inputs_config[1]['label_visibility']
            )
        with col3:
            stock_plate = st.text_input(
                label=inputs_config[2]['label'],
                value=inputs_config[2]['value'],
                key=inputs_config[2]['key'],
                label_visibility=inputs_config[2]['label_visibility'],
                disabled=inputs_config[2]['disabled']
            )
        with col4:
            stock_code = st.text_input(
                label=inputs_config[3]['label'],
                value=inputs_config[3]['value'],
                key=inputs_config[3]['key'],
                label_visibility=inputs_config[3]['label_visibility'],
                disabled=inputs_config[3]['disabled']
            )
        
        common_parts.append({
            'name': selected_name, 
            'volume': volume, 
            'in_source': name_exist, 
            'plate': stock_plate, 
            'well': stock_code
        })
        
        # Validation messages
        if sources is not None and selected_name in sources['name'].values:
            current_vol = sources.loc[sources['name'] == selected_name, ['volume']].values.sum()
            st.success(f"{selected_name} detected {current_vol} in sources")
        elif validate_stock_location(stock_plate, stock_code):
            st.warning(f"Please ensure {selected_name} is available in {stock_plate}, {stock_code}")
        else:
            st.error("Invalid Stock plate or Stock location format. Example) Stock_plate3, A7")
    
    return common_parts

def find_source_well(sources_, name, required_volume):
    sources_row = sources_[(sources_['name'] == name) & (sources_['volume'] >= required_volume)]
    if sources_row.empty:
        st.warning(f"Not enough volume available for '{name}'")
        raise ValueError(f"Not enough volume available for '{name}'")
    row = sources_row.iloc[0]
    sources_.loc[(sources_['name'] == row['name']) & (sources_['plate'] == row['plate']) & (sources_['well'] == row['well']), 'volume'] -= required_volume
    return row['plate'], row['well']

def protocol_to_ot2_script(protocol_rows, metadata, requirements, plate_posit):
    script = f"""
from opentrons import protocol_api

# metadata
metadata = {{
    {metadata}
}}
requirements = {{{requirements}}}

def run(protocol: protocol_api.ProtocolContext):
    # labware_load
    """
    # Labware 위치 설정
    for plate, position in plate_posit[:-1]:
        script += f"{plate} = protocol.load_labware('corning_96_wellplate_360ul_flat', {position})\n    "
    script += f"""
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', {plate_posit[-1][1]})
    p300 = protocol.load_instrument('p300_single', 'left', tip_racks=[tiprack])\n
    """

    for idx, row in protocol_rows.iterrows():
        script += f"""
    # Transfer {row['Component']}
    p300.pick_up_tip()
    p300.aspirate({row['Volume']}, {row['Asp.Rack']}['{row['Asp.Posi']}'])  # {row['Note']}
    p300.dispense({row['Volume']}, {row['Dsp.Rack']}['{row['Dsp.Posi']}'])
    p300.drop_tip()
    """
    return script

def generate_protocol(designs, destination_name, sources, plate_type=96, naming = "TU"):
    protocol_rows = pd.DataFrame(columns=["Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"])
    output_rows = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    dest_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]
    dest_row_list = {"6":3, "12":4, "24":6, "48":8, "96":12, "384":24}  
    dest_row_num = dest_row_list.get(str(plate_type))
    volume_error = False
    group_counters = {}  # 그룹별 인덱스 초기화
    for index, design in enumerate(designs):
        if volume_error:
            protocol_rows, output_rows = None, None
            break
        plate_num = int(index/plate_type)
        # st.write(index/plate_type)
        dest_name = destination_name[plate_num]
        plate_index = index - plate_num*plate_type + 1
        # 목적지 웰 설정
        st.write()
        # dest_row = int((plate_index-0.5)//dest_row_num)
        dest_row = math.ceil(plate_index/dest_row_num) - 1

        destination = f"{dest_list[dest_row]}{plate_index - dest_row_num * (dest_row)}"
        
        # 디자인에 그룹 이름을 포함하여 이름 설정
        group_name = design[0]['note']  # 첫 번째 아이템의 note에서 그룹 이름 가져오기
        if group_name not in group_counters:
            group_counters[group_name] = 1  # 새로운 그룹이면 인덱스 초기화
        else:
            group_counters[group_name] += 1  # 기존 그룹이면 인덱스 증가

        protocol_row = {
            "Component": f"{naming + "_" if naming is not None else ""}{group_name}_{group_counters[group_name]}",
            "Asp.Rack": "",
            "Asp.Posi": "",
            "Dsp.Rack": dest_name,
            "Dsp.Posi": destination,
            "Volume": 0,
            "Note": group_name
        }
        
        # st.write(design)
    
        output_row = {
            "name": f"{design[0]['name']}-{design[1]['name']}-{design[2]['name']}-{design[3]['name']}" if naming == "TU" else f"{naming}_{group_name}_{group_counters[group_name]}",
            "plate": dest_name,
            "well": destination,
            "volume": 0,
            "note": f"{naming}_{group_name}_{group_counters[group_name]}"
        }
        
        # 디자인에서 소스 데이터 추출
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']

            try:
                plate, well = find_source_well(sources, name, vol)
            except ValueError:
                total_need = sum(item['volume'] for design in designs for item in design if item['name'] == name)
                total_have = sources.loc[sources['name'] == name, 'volume'].sum()
                st.error(f"total {total_have}ul in sources when {total_need}ul need")
                volume_error = True
                break

            protocol_row["Asp.Rack"] = plate
            protocol_row["Asp.Posi"] = well
            protocol_row["Note"] = name
            protocol_row["Volume"] = vol
            
            output_row['volume'] += vol
            output_row[k] = name

            protocol_rows = pd.concat([protocol_rows, pd.DataFrame([protocol_row])])
        output_rows = pd.concat([output_rows, pd.DataFrame([output_row])])

    return protocol_rows, output_rows

def validate_stock_location(stock_plate, stock_code):
    """Stock plate와 location 유효성 검사"""
    return stock_plate.strip() != "" and re.match(r'^[A-Ha-h][1-9]$|^[A-Ha-h]1[0-2]$', stock_code)

def load_tu_design_from_json(uploaded_file):
    """Load TU design from JSON file.
    Expected JSON format:
    [
        {
            "group_name": "Group_1",
            "number_of_tu": 3,
            "designs": [
                {
                    "Promoter": ["P1", "P2"],
                    "CDS": ["C1"],
                    "Terminator": ["T1", "T2"]
                },
                ...
            ]
        },
        ...
    ]
    """
    try:
        data = json.load(uploaded_file)
        return data
    except Exception as e:
        st.error(f"Error loading TU design from JSON: {str(e)}")
        return None

def create_design_template_files():
    """Create template files for TU design import."""
    # CSV template - minimal required fields only
    csv_template = """Group,Promoter,CDS,Terminator
Group_1,(P)TDH,(C)mTurquiose2,(T)ENO1
Group_1,(P)RPL18B,(C)Venus,(T)ISSA1
Group_1,(P)RAD27,(C)mRuby2,(T)ADH1
Group_2,(P)CCW12,(C)Cas9,(T)PGK1
Group_2,(P)ALD6,(C)I-Scei,(T)ENO2"""
    
    # JSON template - updated to match new format (Connector is automatically set)
    json_template = [
        {
            "group_name": "Group_1",
            "number_of_tu": 3,
            "designs": [
                {
                    "Promoter": ["(P)TDH"],
                    "CDS": ["(C)mTurquiose2"],
                    "Terminator": ["(T)ENO1"]
                },
                {
                    "Promoter": ["(P)RPL18B"],
                    "CDS": ["(C)Venus"],
                    "Terminator": ["(T)ISSA1"]
                },
                {
                    "Promoter": ["(P)RAD27"],
                    "CDS": ["(C)mRuby2"],
                    "Terminator": ["(T)ADH1"]
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

def validate_source_types(sources):
    """Validate that all required source types are present."""
    for type_item in ['Promoter', 'CDS', 'Terminator', 'Connector']:
        if sources[sources['type'] == type_item].empty:
            st.error(f"No rows with type '{type_item}' found in the sources. Please check your input file.")
            st.stop()

def create_ot2_labware_settings(sheet_names, destination_names, key_prefix):
    """Create OT2 labware position and type settings."""
    labware_options = [
        "corning_96_wellplate_360ul_flat",
        "opentrons_96_tiprack_300ul",
        "biorad_96_wellplate_200ul_pcr",
        "nest_96_wellplate_2ml_deep",
        "usascientific_12_reservoir_22ml",
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap"
    ]
    
    plate_posit = []
    plate_types = []
    
    # Source plates
    for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
        col1, col2 = st.columns(2)
        with col1:
            position = st.selectbox(
                options=range(1, 12), 
                label=f"{plate} position:", 
                index=i, 
                key=f"{key_prefix}_pos_{i}"
            )
        with col2:
            labware_type = st.selectbox(
                f"{plate} labware type", 
                options=labware_options, 
                index=0, 
                key=f"{key_prefix}_labware_type_{i}"
            )
        plate_posit.append([plate, position])
        plate_types.append([plate, labware_type])
    
    # Destination plates
    for i, plate in enumerate(destination_names):
        col1, col2 = st.columns(2)
        with col1:
            position = st.selectbox(
                options=range(1, 12), 
                label=f"{plate} position:", 
                index=i, 
                key=f"{key_prefix}_dpos_{i}"
            )
        with col2:
            labware_type = st.selectbox(
                f"{plate} labware type", 
                options=labware_options, 
                index=0, 
                key=f"{key_prefix}_dlabware_type_{i}"
            )
        plate_posit.append([plate, position])
        plate_types.append([plate, labware_type])
    
    # Tiprack
    plate_posit.append([
        "tiprack", 
        st.selectbox(
            options=range(1, 12), 
            label="Tiprack position:", 
            index=len(sheet_names)+len(destination_names), 
            key=f"{key_prefix}_tiprack"
        )
    ])
    
    return plate_posit, plate_types

def create_ot2_section(protocol, sheet_names, destination_names, key_prefix):
    """Create complete OT2 convert section."""
    with st.expander("OT2 convert:"):
        metadata = st.text_area(
            value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", 
            label="Metadata", 
            key=f'{key_prefix}_metadata'
        ).replace("\n", "\n    ")
        
        requirements = st.text_area(
            value='"robotType": "OT-2", "apiLevel": "2.17"', 
            label="Requirements", 
            key=f'{key_prefix}_requirements'
        )
        
        plate_posit, plate_types = create_ot2_labware_settings(sheet_names, destination_names, key_prefix)
        converted_protocol = protocol_to_ot2_script(protocol, metadata, requirements, plate_posit)
        st.code(converted_protocol, language='python')
        
        return converted_protocol

def load_excel_sources(uploaded_file, plate_names, default_vol):
    """Load sources from Excel file."""
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

        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=sr, index_col=sc)

        for row_index, row in df_sheet.iterrows():
            for col_index, item in row.items():
                if pd.notna(item):
                    data = {
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

def load_csv_sources(uploaded_file):
    """Load sources from CSV file."""
    df = pd.read_csv(uploaded_file, encoding='iso-8859-1')
    sources = pd.DataFrame(columns=["type", "name", "plate", "well", "volume", "note"])
    
    sources['type'] = df['type']
    sources['name'] = df['name']
    sources['plate'] = df['plate']
    sources['well'] = df['well']
    sources['volume'] = df['volume']
    sources['note'] = df['note']
    
    return sources

def validate_source_types(sources):
    """Validate that all required source types are present."""
    for type_item in ['Promoter', 'CDS', 'Terminator', 'Connector']:
        if sources[sources['type'] == type_item].empty:
            st.error(f"No rows with type '{type_item}' found in the sources. Please check your input file.")
            st.stop()


if "commons_row" not in st.session_state:
    st.session_state.commons_row = 1  # 초기 행 수 설정
if "commons_row2" not in st.session_state:
    st.session_state.commons_row2 = 1  # 초기 행 수 설정


st.title("Assembly Design Tool")
st.write("This tool is designed to assist in the assembly design process for synthetic biology projects. It allows users to upload an Excel file containing information about parts and their respective volumes, and then generates assembly designs based on user-defined parameters.")
st.write(">## Input")
if st.checkbox('Legacy_Input', value = False):
    ## 파일 업로드 및 데이터 처리
    uploaded_file = st.file_uploader("Upload your Stocking Plate Excel file", type="xlsx")
    if uploaded_file is None:
        uploaded_file = "./plate_sample.xlsx"
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names

        # plate_name 입력을 한 줄에 배치
        plate_col1, plate_col2 = st.columns([2, 8])
        with plate_col1:
            st.write("Plate name")
        with plate_col2:
            plate_names = [st.text_input(f"Plate {i+1} Name", value=sheet_name, key=f"plate_name_{i}") for i, sheet_name in enumerate(sheet_names)]

        # default volume 입력을 한 줄에 배치
        vol_col1, vol_col2 = st.columns([2, 8])
        with vol_col1:
            st.write("Default volume (ul)")
        with vol_col2:
            default_vol = st.number_input("Default volume", value=10000, min_value=0, step=10, label_visibility="collapsed")

        sources, sheet_names = load_excel_sources(uploaded_file, plate_names, default_vol)
        
        # 플레이트별로 데이터프레임 표시
        with st.expander("Sourceplate"):
            for plate_name, group in sources.groupby('plate'):
                st.subheader(f"Plate: {plate_name}")
                st.dataframe(group)

#############################################################################
else:
    uploaded_file = st.file_uploader("Upload your Stocking Plate CSV file", type="csv")
    if uploaded_file == None:
        uploaded_file = "./SourcePlate_Sample.csv"
    try:
        sourceplate_name = st.text_input("Sourceplate name", value = uploaded_file.name.split(".")[0])
    except:
        sourceplate_name = "source"

    if uploaded_file != None:
        sources = load_csv_sources(uploaded_file)
        st.dataframe(sources)
        validate_source_types(sources)
        sheet_names = sources['plate'].unique().tolist()  # For compatibility with OT2 functions
####################################################################################
sources_org = sources.copy()

st.write("")
st.write("")
st.write("")
st.write(">## Assembly Design")

# 볼륨 입력
st.write("="*100)
## maximum volume of single well
st.write("### Maximum volume of single well")
st.write("Specify the maximum volume of each well in the lv1 output. Default is 50ul for 96 well plate.")
lv1_maxvol = st.number_input(label = "Maximum volume for each TU", min_value = 0., value = 50., step = 0.1, label_visibility="collapsed")
## deadvolume setting
st.write("### Deadvolume")
st.write("Specify the dead volume of each well in the lv1 output. Recommended to be larger than 2ul.")
lv2_deadvol = st.number_input(label = "Dead volume for each TU", min_value = 0., value = 2., step = 0.1, label_visibility="collapsed")
# st.session_state.lv2_deadvol = lv2_deadvol
st.write("="*100)

# Initialize session state for design data
if "loaded_design_data" not in st.session_state:
    st.session_state.loaded_design_data = None
if "design_file_loaded" not in st.session_state:
    st.session_state.design_file_loaded = False
if "widget_key_suffix" not in st.session_state:
    st.session_state.widget_key_suffix = 0

# File upload section for TU design (moved above Groups section)
with st.expander("Load TU Design from File (Optional)"):
    st.write("You can upload a CSV or JSON file to load predefined TU designs. The uploaded design will be used as initial values for Groups and TU design.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Upload Design File:**")
        design_file = st.file_uploader(
            "Choose a file", 
            type=['csv', 'json'], 
            key="design_file_uploader",
            help="Upload CSV or JSON file with TU design data"
        )
        
        if design_file is not None:
            file_extension = design_file.name.split('.')[-1].lower()
            
            if file_extension == 'csv':
                loaded_data = load_tu_design_from_csv(design_file)
            elif file_extension == 'json':
                loaded_data = load_tu_design_from_json(design_file)
            else:
                st.error("Unsupported file format. Please upload CSV or JSON files.")
                loaded_data = None
            
            if loaded_data:
                # Check if this is a new file upload (not the same as before)
                if st.session_state.loaded_design_data != loaded_data:
                    st.session_state.loaded_design_data = loaded_data
                    st.session_state.design_file_loaded = True
                    # Increment the key suffix to force widget refresh
                    st.session_state.widget_key_suffix += 1
                    st.success(f"Successfully loaded {len(loaded_data)} group(s) from {design_file.name}")
                    
                    # Display loaded data preview
                    for i, group in enumerate(loaded_data):
                        st.write(f"**Group {i+1}:** {group['group_name']} ({group['number_of_tu']} TUs)")
                    
                    # Rerun to refresh all widgets with new data
                    st.rerun()
                else:
                    st.success(f"Using loaded design with {len(loaded_data)} group(s)")
                    for i, group in enumerate(loaded_data):
                        st.write(f"**Group {i+1}:** {group['group_name']} ({group['number_of_tu']} TUs)")
    
    with col2:
        st.write("**Download Template Files:**")
        
        # Create template files
        csv_template, json_template = create_design_template_files()
        
        # Download buttons for templates
        st.download_button(
            label="Download CSV Template",
            data=csv_template,
            file_name="tu_design_template.csv",
            mime="text/csv",
            help="Download a CSV template file to fill in your TU design"
        )
        
        import json
        json_str = json.dumps(json_template, indent=2)
        st.download_button(
            label="Download JSON Template", 
            data=json_str,
            file_name="tu_design_template.json",
            mime="application/json",
            help="Download a JSON template file to fill in your TU design"
        )

st.write("### Groups")
# 사용자에게 그룹 지정 옵션 제공
user_defined_groups = []
user_defined_groups_nop = []
user_defined_groups_roa = []

# Set default values from loaded data if available
default_num_groups = 1
if st.session_state.loaded_design_data:
    default_num_groups = len(st.session_state.loaded_design_data)

# 사용자 정의 그룹 수 입력을 한 줄에 배치
group_col1, group_col2 = st.columns([2, 8])
with group_col1:
    st.write("* Number of groups")
with group_col2:
    num_groups = st.number_input("Number of groups", min_value=1, value=default_num_groups, step=1, label_visibility="collapsed")

# 각 그룹에 대해 사용자로부터 입력받기
group_col1, group_col2, group_col3, group_col4 = st.columns([2, 3, 2, 2])
with group_col2:
    st.write("Group names")
with group_col3:
    st.write("Number of TU")
with group_col4:
    st.write("Repeats of assembly")

for i in range(num_groups):
    # Set default values from loaded data if available
    default_group_name = f"Group_{i+1}"
    default_group_nop = 3
    
    if st.session_state.loaded_design_data and i < len(st.session_state.loaded_design_data):
        loaded_group = st.session_state.loaded_design_data[i]
        default_group_name = loaded_group['group_name']
        default_group_nop = loaded_group['number_of_tu']
    
    group_col1, group_col2, group_col3, group_col4 = st.columns([2, 3, 2, 2])
    with group_col1:
        st.write(f"* Group {i+1}")
    with group_col2:
        group_name = st.text_input(f"Group {i+1} Name", value=default_group_name, key=f"group_name_{i}_{st.session_state.widget_key_suffix}", label_visibility="collapsed")
        user_defined_groups.append(group_name)
    with group_col3:
        group_nop = st.number_input(f"Number of TU", value=default_group_nop, key=f"Group_noa{i}_{st.session_state.widget_key_suffix}", min_value=1, step=1, label_visibility="collapsed")
        user_defined_groups_nop.append(group_nop)
    with group_col4:
        group_roa = st.number_input(f"Repeats of assembly", value=1, key=f"Group_roa{i}_{st.session_state.widget_key_suffix}", min_value=1, step=1, label_visibility="collapsed", disabled=True)
        user_defined_groups_roa.append(group_roa)

# TU designs
st.write("### TU design")

designs = []

## connector 순서 및 그룹 설정
connector_ex = sources[sources['name'].str.startswith('(N)s', na=False) | sources['name'].str.endswith('e', na=False)]['name'].drop_duplicates().sort_values().tolist()
connector_ex = sorted(connector_ex, key=lambda x: [0 if c.isalpha() else 1 for c in x])
connector_endo = sources[(~sources['name'].isin(connector_ex)) & sources['name'].str.startswith('(N)', na=False)]['name'].drop_duplicates().sort_values().tolist()
connector_options = connector_ex + connector_endo

# 선택 상자 생성
options = {
    "Promoter": sources[sources['type'] == "Promoter"]['name'].drop_duplicates().tolist(),
    "CDS": sources[sources['type'] == "CDS"]['name'].drop_duplicates().tolist(),
    "Terminator": sources[sources['type'] == "Terminator"]['name'].drop_duplicates().tolist(),
    "Connector": connector_options
}

design_df = pd.DataFrame(columns=["Promoter", "CDS", "Terminator", "Connector", "Group", "tu_usage"])
selected_group = []
cols = 4 
for g, group_name in enumerate(user_defined_groups):
    st.write(f"* Design for {group_name}")
    # 카테고리 이름 설정
    cols_placeholder = st.columns(cols)
    for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
        with cols_placeholder[col]:
            st.write(category)
    rows = user_defined_groups_nop[g]
    selected_row = []
    for row in range(rows):
        cols_placeholder = st.columns(cols)

        selected_items = {}
        for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
            with cols_placeholder[col]:
                # Get default values from loaded data if available
                default_values = []
                if (st.session_state.loaded_design_data and 
                    g < len(st.session_state.loaded_design_data) and 
                    row < len(st.session_state.loaded_design_data[g]['designs'])):
                    loaded_design = st.session_state.loaded_design_data[g]['designs'][row]
                    default_values = loaded_design.get(category, [])
                    # Filter to only include values that exist in options
                    default_values = [v for v in default_values if v in options[category]]
                
                if category == "Connector":
                    items = options[category]
                    # For connectors, use single selection with loaded default or original logic
                    if default_values:
                        default_index = connector_options.index(default_values[0]) if default_values[0] in connector_options else 0
                    else:
                        default_index = (
                            connector_options.index(connector_ex[0]) if row == 0   # 첫 번째 행
                            else connector_options.index(connector_ex[row]) if row == rows - 1 # 마지막 행
                            else connector_options.index(connector_endo[row-1])  # 그 외
                        )
                    
                    selected_items[category] = [st.selectbox(
                        category,
                        items,
                        key=f"select_{row}_{col}_{g}_{st.session_state.widget_key_suffix}",
                        index=default_index,
                        label_visibility="collapsed",
                        disabled=True
                    )]

                else:
                    items = options[category]
                    selected_items[category] = st.multiselect(
                        category,
                        items,
                        default=default_values,  # Use loaded default values
                        key=f"select_{row}_{col}_{g}_{st.session_state.widget_key_suffix}",
                        label_visibility="collapsed",
                        # max_selections= 1 if category == "CDS" else None
                    )
                    if not selected_items[category]:
                        selected_items[category] = [""]

        selected_row.append(selected_items)

        selected_items_comb = product(
            selected_items["Promoter"],
            selected_items["CDS"],
            selected_items["Terminator"],
            selected_items["Connector"]
        )

        for combi in selected_items_comb:
            design_df = pd.concat([design_df, pd.DataFrame([{
                "Promoter": combi[0],
                "CDS": combi[1],
                "Terminator": combi[2],
                "Connector": combi[3],
                "Group": g,
                "tu_usage": 0
            }])], ignore_index=True)
    selected_group.append(selected_row)

design2_list = []
for group_no, group_df in design_df.groupby('Group'):
    TU_list = []
    for connector_no, connector_group in group_df.groupby('Connector'):
        tu_by_con = []
        for _, row in connector_group.iterrows():
            tu_by_con.append({"P":row['Promoter'], "C":row["CDS"], "T":row["Terminator"], "N":row["Connector"]})
        TU_list.append(tu_by_con)
    for item in product(*TU_list):
        elements = [elem for sublist in item for elem in sublist.values()]
        if len(set(elements)) == 4*user_defined_groups_nop[group_no]:
            design2_list.append([group_no, item])
            for k in range(user_defined_groups_nop[group_no]):  
                design_df.loc[
                    (design_df['Promoter'] == item[k]['P']) &
                    (design_df['CDS'] == item[k]['C']) &
                    (design_df['Terminator'] == item[k]['T']) &
                    (design_df['Connector'] == item[k]['N']) &
                    (design_df['Group'] == group_no),
                    'tu_usage'
                ] += 1

# st.write(design_df)
# st.write(design2_list)
# Group by the relevant columns and sum the 'tu_usage' column
design_df = design_df.groupby(["Promoter", "CDS", "Terminator", "Connector"]).agg({
    "Group": "first",
    "tu_usage": "sum"
}).reset_index()
st.success(f"{len(design_df)} of TU, {len(design2_list)} of Lv2 design")
# st.write(design_df)
# st.write(design2_list)

st.write("### TU parts")
st.write("Specify the volume for each part in the TU design. The default volume is 2ul.")
vols = []
cols_placeholder = st.columns(cols)
for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
    with cols_placeholder[col]:
        vols.append(st.number_input(label=category, value=2., step=0.1, min_value=0., key=f"vols_{col}"))

st.write("")

# 공통 부품 추가
st.write('''Set the parts to be included in every Lv1 TU. Specify the plate name and location.  
            (If the part name exists in the source, that source will be used.)
            ''')
commons = create_common_parts_section(
    "Lv1 Common parts", 
    "commons_row", 
    "GGAmixture", 
    "GGAmix_plate", 
    sources
)

for i in range(3):
    st.write("")

# 총 볼륨 계산
total_vol = sum(common['volume'] for common in commons) + sum(vols)
st.success(f"total {total_vol}ul of each TU")
# st.session_state.total_vol = total_vol

for i in range(5):
    st.write("")

## lv2 commons
st.write('''Set the parts to be included in every Lv2 outputs. Specify the plate name and location.  
            (If the part name exists in the provided source, it will be used.)''')

lv2_commons = create_common_parts_section(
    "Lv2 Common parts", 
    "commons_row2", 
    "Vector", 
    "Vector_plate", 
    sources
)

# Volume validation for Lv2
for common in lv2_commons:
    if total_vol*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons) > lv1_maxvol:
        st.warning(f"Warning: Total volume({total_vol*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons)}ul) is too high(>{lv1_maxvol})!")


## add common parts to sources
# Calculate the required volume for each TU
design_df['need_vol'] = design_df['tu_usage'] * total_vol
# Calculate the number of wells required for each TU
design_df['wells_required'] = (design_df['need_vol'] / (lv1_maxvol - lv2_deadvol)).apply(lambda x: int(x) + (x % 1 > 0))
design_df['wells_required'] = design_df['wells_required'].apply(lambda x: 1 if x == 0 else x) ## prevent division by zero errors
design_df['volume_for_each_well'] = design_df['need_vol'] / design_df['wells_required'] + lv2_deadvol 
design_df['total_vol'] = design_df['wells_required'] * design_df['volume_for_each_well']
ratepoint = round(sum(design_df['total_vol'])/total_vol, 2)

for common in commons:
    if not common['in_source']:
        common_source = pd.DataFrame([{
        "name": common['name'],
        "plate": common['plate'],
        "well": common['well'],
        "volume": common['volume']*ratepoint + lv2_deadvol,
        "note": "common part added"
        }])
        # st.write(common_source)
        sources = pd.concat([sources, common_source], ignore_index=True)

for common2 in lv2_commons:
    if not common2['in_source']:
        common2_source = pd.DataFrame([{
        "name": common2['name'],
        "plate": common2['plate'],
        "well": common2['well'],
        "volume": (common2['volume']+lv2_deadvol) * len(design2_list),
        "note": "common part added"
        }])
        # st.write(common2_source)
        sources = pd.concat([sources, common2_source], ignore_index=True)

## summary designs
# with st.expander("Summary"):
#     st.write(design_df)
#     st.write(design2_list)
#     st.write(f"Total {len(design_df)} of TU, {len(design2_list)} of Lv2 design")
#     st.write(f"total volume for single TU: {total_vol}ul")
#     st.write(f"total volume for single Lv2: {total_vol*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons)}ul")
#     st.write(f"lv1_commons: {commons}")
#     st.write(f"lv2_deadvol: {lv2_deadvol}ul")
#     st.write(f"lv2_commons: {lv2_commons}")
#     st.write("")    
#     st.write(f"total TU usage: {sum(design_df['tu_usage'])}")
    
#     ## 어..그러니까..
#     st.write(f"total volume for all TU: {sum(design_df['total_vol'])}ul")
#     st.write(f"ratepoint: {ratepoint}")
#     st.write(f"common vol of entire volume: {sum(design_df['total_vol'])*(commons[0]['volume']/total_vol)}ul")
#     st.write(f"ratepoint: {ratepoint}")
#     st.write(design_df)


for i in range(2):
    st.write("")


### generate outputs
if st.button("Apply Designs", key="apply_button"):
    st.session_state.apply_clicked = True

for i in range(5):
    st.write("")

if st.session_state.get("apply_clicked", False): 
    
    # Convert DataFrame to designs format
    # st.write(design_df)
    designs = []
    tu_per_single_well = int((lv1_maxvol-lv2_deadvol)/total_vol)
    for _, row in design_df.iterrows():
        row_useage = row["tu_usage"]
        while row_useage > 0:
            if row_useage >= tu_per_single_well:
                tu_con = tu_per_single_well
            else:
                tu_con = row_useage
            row_useage -= tu_con
            
            row_design = []
            for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
                if row[category] != "":
                    row_design.append({'name': row[category], 'volume': round(vols[col]*tu_con+(lv2_deadvol*vols[col]/total_vol), 2)})
            for common in commons:
                common_a = {'name': common['name'], 'volume': round(common['volume']*tu_con+(lv2_deadvol*common['volume']/total_vol), 2)}
                row_design += [common_a]
            for repeat in range(user_defined_groups_roa[row["Group"]]):
                design_with_note = [{'name': item['name'], 'volume': item['volume'], 'note': row["Group"]} for item in row_design]
                designs.append(design_with_note)


    st.write("## Outputs")
    st.write("#### Lv1")
    lv1_sources = sources.copy()

    lv1_plate_type = int(st.selectbox(label='Destination plate type', options=["6", "12", "24", "48", "96", "384"], index=4, key="lv1_plate_type"))
    # lv1_plate_len = int((len(designs)-0.5)/lv1_plate_type)+1
    lv1_plate_len = math.ceil(len(designs)/lv1_plate_type)
    # st.write(len(designs), plate_type, plate_len)

    lv1_destination_names = []
    for plate_num in range(lv1_plate_len):
        lv1_destination_names.append(st.text_input(f"Destination Plate {plate_num+1} Name", value=f"Lv1_destination_{plate_num+1}", key = f"lv1_destination_name_{plate_num}"))
    
    lv1_protocol, lv1_outputs = generate_protocol(designs, lv1_destination_names, lv1_sources, plate_type=lv1_plate_type)
    
    for common in commons:
        if not common['in_source']:
            common_sum = lv1_protocol[lv1_protocol['Note']==common]['Volume'].sum()
            st.warning(f"please ensure that minimum {round(common['volume']*ratepoint,2)}ul of {common['name']} is available in {common['plate']}, {common['well']} (+10ul or more is recommended)")

    st.write("Generated Lv1 mapping:")
    st.write(lv1_protocol.reset_index(drop=True))
    with st.expander("Generated Lv1 output plate (*for reference):"):
        st.write(lv1_outputs.reset_index(drop=True))
    
    # OT2 convert section
    create_ot2_section(lv1_protocol, sheet_names, lv1_destination_names, "lv1")


    st.write("#### Lv2")
    designs2 = []
    
    for comb in design2_list: # group
        group, items = comb
        row_design = [{'name': f"{item['P']}-{item['C']}-{item['T']}-{item['N']}", 'volume': total_vol, 'note': user_defined_groups[group]} for item in items]
        row_design += lv2_commons
        designs2.append(row_design)

    lv2_plate_type = int(st.selectbox(label='Destination plate type', options=["6", "12", "24", "48", "96", "384"], index=4, key="lv2_plate_type"))
    # lv2_plate_len = int((len(designs2)-0.5)/lv2_plate_type)+1
    lv2_plate_len = math.ceil(len(designs2)/lv2_plate_type)
    # st.write(len(designs), lv2_plate_type , lv2_plate_len)

    for common2 in lv2_commons:
        if not common2['in_source']:
            # st.write(common)
            st.warning(f"please ensure that minimum {round(common2['volume']*len(designs2),2)}ul of {common2['name']} is available in {common2['plate']}, {common2['well']} (+10ul or more is recommended)")



    lv2_destination_names = []
    for plate_num in range(lv2_plate_len):
        lv2_destination_names.append(st.text_input(f"Destination Plate {plate_num+1} Name", value=f"Lv2_destination_{plate_num+1}", key = f"lv2_destination_name_{plate_num}"))
    

    lv2_sources = pd.concat([lv1_sources, lv1_outputs])
    # st.write(lv2_destination_names)
    lv2_protocol, lv2_outputs = generate_protocol(designs2, lv2_destination_names, lv2_sources, plate_type=lv2_plate_type, naming=None)

    
    st.write("Generated Lv2 mapping:")
    st.write(lv2_protocol.reset_index(drop=True))
    with st.expander("Generated Lv2 output plate:"):
        st.write(lv2_outputs.reset_index(drop=True))
    

    st.write("updated sources:")
    st.write(lv2_sources.reset_index(drop=True))

    # OT2 convert section
    create_ot2_section(lv2_protocol, sheet_names, lv2_destination_names, "lv2")
