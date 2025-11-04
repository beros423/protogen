import streamlit as st
import pandas as pd
import os
import json
from itertools import product
from functions import find_source_well, generate_ot2_protocol, generate_janus_protocol

## setup theme
st.set_page_config(layout = "wide")

# Helper functions for design file loading
def load_design_from_csv(uploaded_file):
    """Load assembly design from CSV file.
    New format: each row is one assembly, each column is a part type
    Supports multiple parts per cell separated by semicolon (;)
    Example:
    Promoter,CDS,Terminator,Backbone
    pTrc;pLac,gfp,rrnB_T1,pUC19
    pBAD,rfp;bfp,rrnB_T2,pBR322
    """
    try:
        df = pd.read_csv(uploaded_file)
        
        # Extract part types from header (columns)
        part_types = [col for col in df.columns if col != 'Group']
        
        # Process each row as one assembly design
        design_data = []
        assemblies = []
        
        for row_idx, row in df.iterrows():
            assembly_parts = {}
            
            for part_type in part_types:
                # Get cell value and split by semicolon for multiple options
                cell_value = str(row.get(part_type, '')).strip()
                if cell_value and cell_value != 'nan':
                    # Split by semicolon and clean up whitespace
                    parts_list = [part.strip() for part in cell_value.split(';') if part.strip()]
                    assembly_parts[part_type] = parts_list
                else:
                    assembly_parts[part_type] = []
            
            if any(assembly_parts.values()):  # Only add if at least one part is specified
                assemblies.append(assembly_parts)
        
        # Return in the expected format
        if assemblies:
            design_data.append({
                'group_name': 'Loaded_Design',
                'assemblies': assemblies,
                'part_types': part_types
            })
        
        return design_data
        
    except Exception as e:
        st.error(f"Error loading design from CSV: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error loading design from CSV: {str(e)}")
        return None

def load_design_from_json(uploaded_file):
    """Load assembly design from JSON file."""
    try:
        data = json.load(uploaded_file)
        return data
    except Exception as e:
        st.error(f"Error loading design from JSON: {str(e)}")
        return None

def create_design_template_files():
    """Create template files for design import."""
    # CSV template for universal assembly - supports multiple parts per cell
    csv_template = """Promoter,CDS,Terminator,Backbone
pTrc;pLac,gfp,rrnB_T1,pUC19
pBAD,rfp;bfp,rrnB_T2,pBR322
pTet,yfp,dbl_term,pBR322"""
    
    # JSON template for universal assembly
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
    
    return csv_template, json_template


####################################################################################
## file load

uploaded_file = st.file_uploader("Upload your Stocking Plate CSV file", type="csv")
if uploaded_file is None:
    # Try to use default file if it exists
    default_file = "./SourcePlate_Sample.csv"
    if os.path.exists(default_file):
        uploaded_file = default_file
    else:
        st.warning("Please upload a stocking plate CSV file to continue.")
        st.stop()

sourceplate_name = "source"

# st.write(uploaded_file)
if uploaded_file is not None:
    if isinstance(uploaded_file, str):
        # File path string
        df = pd.read_csv(uploaded_file, encoding = "utf-8")
    else:
        # Uploaded file object
        df = pd.read_csv(uploaded_file, encoding = "utf-8")
    # st.write(df)
    # default_vol = st.number_input("default volume", value = 100, min_value = 0, step = 10)
    
    sources = pd.DataFrame(columns = ["type", "name","plate", "well", "volume","note"])
    
    sources['type'] = df['type']
    sources['name'] = df['name']
    sources['plate'] = df['plate']
    sources['well'] = df['well']
    sources['volume'] = df['volume']
    sources['note'] = df['note']

    st.dataframe(sources)

########################################################################################
    ## Design setting
    
    st.write("")
    st.write("")
    st.write("")
    st.subheader("Protocol Design")

    # Initialize session state for design data
    if "loaded_design_data" not in st.session_state:
        st.session_state.loaded_design_data = None

    # File upload section for design
    with st.expander("Load Assembly Design from File (Optional)"):
        st.write("Upload a CSV or JSON file to load pre-defined assembly designs.")
        
        # Template file download
        col1, col2 = st.columns(2)
        with col1:
            csv_template, json_template = create_design_template_files()
            st.download_button(
                label="Download CSV Template",
                data=csv_template,
                file_name="assembly_design_template.csv",
                mime="text/csv"
            )
        with col2:
            st.download_button(
                label="Download JSON Template", 
                data=json.dumps(json_template, indent=2),
                file_name="assembly_design_template.json",
                mime="application/json"
            )
        
        # File upload
        design_file = st.file_uploader(
            "Choose design file",
            type=['csv', 'json'],
            key="design_file_uploader"
        )
        
        if design_file is not None:
            if design_file.name.endswith('.csv'):
                loaded_data = load_design_from_csv(design_file)
            elif design_file.name.endswith('.json'):
                loaded_data = load_design_from_json(design_file)
            else:
                loaded_data = None
                st.error("Unsupported file format")
            
            if loaded_data:
                st.session_state.loaded_design_data = loaded_data
                st.success(f"✅ Loaded {len(loaded_data)} design group(s)")
                
                # Preview loaded data (without nested expander)
                st.write(loaded_data)
                for group in loaded_data:
                    st.write(f"**{group['group_name']}** ({len(group['assemblies'])} assemblies)")
                    st.write(f"Part types: {', '.join(group['part_types'])}")
                    
                    for i, assembly in enumerate(group['assemblies']):
                        parts_list = []
                        for part_type in group['part_types']:
                            if part_type in assembly and assembly[part_type]:
                                parts_str = ';'.join(assembly[part_type])
                                parts_list.append(f"{part_type}: {parts_str}")
                        st.write(f"  Assembly {i+1}: {' | '.join(parts_list)}")

    ## 조건 설정
    assembly_set_col = st.columns(2)
    with assembly_set_col[0]:
        # Suggest number of assemblies from loaded data if available
        default_rows = 3
        if st.session_state.loaded_design_data:
            suggested_rows = len(st.session_state.loaded_design_data[0]['assemblies'])
            st.info(f"Loaded design has {suggested_rows} assemblies")
            default_rows = suggested_rows
        rows = st.number_input(label="Number of assembly", value=default_rows, min_value=1)
        
    with assembly_set_col[1]:
        # Suggest number of parts from loaded data if available
        default_cols = 4
        if st.session_state.loaded_design_data:
            suggested_cols = len(st.session_state.loaded_design_data[0]['part_types'])
            st.info(f"Loaded design has {suggested_cols} part types")
            default_cols = suggested_cols
        cols = st.number_input(label = "Parts of each wells", value = default_cols, step = 1, min_value = 0)


    ## 
    repeats = st.number_input(label="Repeats of each assembly", value = 1, min_value = 1, step = 1)
    

    # 공통으로 넣을 거
    # st.write("#### volumes", unsafe_allow_html=True)
    types = sources['type'].drop_duplicates().tolist()

    if "commons_row" not in st.session_state:
        st.session_state.commons_row = 1
    
    st.write(f"Common parts [{st.session_state.commons_row}]")

    commons = []
    for row in range(st.session_state.commons_row):
        col1, col2 , col3 = st.columns([3, 3, 2])
        with col1:
            select_type = st.selectbox(label="type", options=types, key = f"select_type_{row}", label_visibility = "collapsed")
            other_selects = sources[sources['type'] == select_type]['name'].drop_duplicates().tolist()
        with col2:
            selected_name = st.selectbox(label="name", options=other_selects, key=f"select_name_{row}", label_visibility="collapsed")
        with col3:
            volume = round(st.number_input(label="vol", value=1.0, step = 0.10, key=f"volume_{row}", label_visibility="collapsed", min_value = 0.0), 2)
        commons.append({'name':selected_name, 'volume':volume})
    ## add/del rows of commons
    col1, col2 = st.columns([1, 9])
    with col1: 
        if st.button('add'):
            st.session_state.commons_row = st.session_state.commons_row + 1
            st.rerun()
    with col2: 
        if st.button('del') and st.session_state.commons_row>= 1:
            st.session_state.commons_row = st.session_state.commons_row - 1
            st.rerun()

    ## volumes input
    labels = []
    vols = []
    
    cols_placeholder = st.columns(cols)
    for col, category in enumerate(labels):
        with cols_placeholder[col]:
            st.write(category)
    st.write("types")
    cols_placeholder = st.columns(cols)
    categories = types
    
    for col in range(cols):
        with cols_placeholder[col]:
            # Set default category from loaded design if available
            default_category_index = 0
            if st.session_state.loaded_design_data and col < len(st.session_state.loaded_design_data[0]['part_types']):
                loaded_part_type = st.session_state.loaded_design_data[0]['part_types'][col]
                if loaded_part_type in categories:
                    default_category_index = categories.index(loaded_part_type)
            
            selected_category = st.selectbox(
                label="type", 
                options=categories, 
                index=default_category_index,
                key=f"select_part1_{col}", 
                label_visibility="collapsed"
            )
            labels.append(selected_category)
            vols.append(round(st.number_input(
                label="volume", 
                value=1., 
                step=0.1, 
                min_value=0., 
                key=f"vols_{col}", 
                label_visibility="collapsed"
            ), 2))
    
    
    #####################################
    total_vol = 0
    for common in commons:
        total_vol += common['volume']
    for vol in vols:
        total_vol += vol
    st.write(f"[ total {total_vol}ul of each well ]")
    #####################################

    ## design 생성
    designs = []
    
    # Show info if loaded design data is available
    if st.session_state.loaded_design_data:
        loaded_assemblies = st.session_state.loaded_design_data[0]['assemblies']
    else:
        loaded_assemblies = []
    
    # Single unified design generation loop
    for row in range(rows):
        cols_placeholder = st.columns(cols)
        selected_items = {}
        
        for col, category in enumerate(labels):
            with cols_placeholder[col]:
                items = sources[sources['type'] == category]['name'].drop_duplicates().tolist()
                
                # Set default selection from loaded data if available
                default_selection = []
                if row < len(loaded_assemblies) and category in loaded_assemblies[row]:
                    loaded_parts = loaded_assemblies[row][category]
                    # Filter only parts that exist in sources
                    default_selection = [part for part in loaded_parts if part in items]
                
                selected_items[col] = st.multiselect(
                    category,
                    items,
                    key=f"select_{row}_{col}",
                    default=default_selection,
                    label_visibility="collapsed",
                )
                if not selected_items[col]:
                    selected_items[col] = [""]
        
        # Generate combinations for this assembly
        selected_items_comb = product(*(selected_items[col] for col in range(len(labels))))
        
        for combi in selected_items_comb:
            row_design = []
            for col, (category, item) in enumerate(zip(labels, combi)):
                if item != "":
                    row_design.append({'name': item, 'volume': vols[col]})
            row_design = row_design + commons
            for repeat in range(repeats):
                designs.append(row_design)
    
    with st.expander("designs"):
        st.write(designs)

    ########################################################################################################
    ########################################################################################################
    # sources_ot2 = sources.copy()
    sources_janus = sources.copy()
    # ### OT2 protocol
    # with st.expander("OT2 protocol"):
    #     metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label = "Metadata").replace("\n", "\n    ")
    #     requirements = st.text_area(value = '"robotType": "OT-2", "apiLevel": "2.17"', label = "Requirements")

    #     plate_posit = []
    #     for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
    #         position = st.selectbox(options = range(1,12), label = f"{plate} position:", index = i)
    #         plate_posit.append([plate, position])
    #     plate_posit.append(["destination", st.selectbox(options = range(1,12), label = "destination_rack position:", index = i+1)])
    #     plate_posit.append(["tiprack", st.selectbox(options = range(1,12), label = "tibrack position:", index = i+2)])

    #     # OT-2 프로토콜 생성 함수
    #     protocol_code, lv1_outputs = generate_ot2_protocol(sources_ot2 , designs, plate_posit, metadata, requirements, sources)

    #     st.write("generated protocol:")
    #     st.code(protocol_code, language='python')
    #     st.write("generated output plate:")
    #     st.write(lv1_outputs)

    ### janus protocol
    st.write("#### output::Janus mapping")
    dplate1_name = st.text_input("destination plate name", value = "dest_01")
    plate_type = st.selectbox(label = "destination plate type", options = [96, 384], index = 0)
    protocol, lv1_outputs = generate_janus_protocol(sources_janus, designs, dplate1_name, sources, plate_type)
    st.write("generated protocol:")
    st.write(protocol)
    st.write("generated output plate:")
    st.write(lv1_outputs)
    st.write("updated sources")
    st.write(sources_janus)

    ########################################################################################################
    ########################################################################################################
    for i in range(7):
        st.write("")
