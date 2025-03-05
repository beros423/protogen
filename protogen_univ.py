import streamlit as st
import pandas as pd
import os
from itertools import product
from functions import find_source_well, generate_ot2_protocol, generate_janus_protocol

## setup theme
st.set_page_config(layout = "wide")


####################################################################################
## file load

uploaded_file = st.file_uploader("Upload your Stocking Plate CSV file", type="csv")
if uploaded_file == None:
    uploaded_file = "./2025-03-05T02-05_export.csv"
# try:
#     sourceplate_name = st.text_input("Sourceplate name", value = os.path.splitext(os.path.basename(uploaded_file))[0])
# except:
#     sourceplate_name = "source"

sourceplate_name = "source"

st.write(uploaded_file)
if uploaded_file != None:
    df = pd.read_csv(uploaded_file, encoding = "euc-kr")
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

    ## 조건 설정
    assembly_set_col = st.columns(2)
    with assembly_set_col[0]:
        rows = st.number_input(label="Number of assembly", value=3, min_value=1)
    with assembly_set_col[1]:
        cols = st.number_input(label = "Parts of each wells", value = 4, step = 1, min_value = 0)


    ## 
    repeats = st.number_input(label="Repeats of each assembly", value = 1, min_value = 1, step = 1)
    

    # 공통으로 넣을 거
    # st.write("#### volumes", unsafe_allow_html=True)
    types = sources['type'].drop_duplicates().tolist()

    if "commons_row" not in st.session_state:
        st.session_state.commons_row = 1  # 초기 행 수 설정
    
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
            labels.append(st.selectbox(label = "type", options = categories, key = f"select_part1_{col}", label_visibility="collapsed"))
            vols.append(round(st.number_input(label = "volume", value = 1., step = 0.1, min_value = 0., key=f"vols_{col}", label_visibility="collapsed"), 2))
    
    
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
    for row in range(rows):
        cols_placeholder = st.columns(cols)

        selected_items = {}
        for col, category in enumerate(labels):
            with cols_placeholder[col]:
                items = sources[sources['type'] == category]['name'].drop_duplicates().tolist()
                selected_items[col] = st.multiselect(
                    category,
                    items,
                    key=f"select_{row}_{col}",
                    # default=[items[0]] if items else [],
                    label_visibility="collapsed",
                )
                if not selected_items[col]:
                    selected_items[col] = [""]
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
