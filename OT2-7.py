import streamlit as st
import pandas as pd
import os
from itertools import product


## setup theme
st.set_page_config(layout = "wide")


def find_source_well(sources_, name, required_volume):
    sources_row = sources_[(sources_['name'] == name) & (sources_['volume'] >= required_volume)]
    if sources_row.empty:
        st.warning(f"Not enough volume available for '{name}'")
        raise ValueError(f"Not enough volume available for '{name}'")
    row = sources_row.iloc[0]
    sources_.loc[(sources_['name'] == row['name']) & (sources_['plate'] == row['plate']) & (sources_['well']==row['well']), 'volume'] -= required_volume  # Update the remaining volume
    return row['plate'], row['well']  # Return plate and well



def generate_ot2_protocol(sources_ot2, designs, plate_posit, metadata, requirements, sources):
    output_designs = pd.DataFrame(columns=["name","plate","well","volume","note"])
    protocol_script = f"""
from opentrons import protocol_api

# metadata
metadata = {{
    {metadata}
}}

requirements = {{{requirements}}}


def run(protocol: protocol_api.ProtocolContext):
    # labware_load
    """
    
    # Labware positioning
    for plate, position in plate_posit[:-1]:
        protocol_script += f"{plate} = protocol.load_labware('corning_96_wellplate_360ul_flat', {position})\n    "
    
    protocol_script += f"""
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', {plate_posit[-1][1]})
    p300 = protocol.load_instrument('p300_single', 'left', tip_racks=[tiprack])\n
    """
    volume_error = False
    for index, design in enumerate(designs):
        
        if volume_error:
            protocol_script = "error"
            output_designs = pd.DataFrame()
            break
        # set target destination well
        dest_list = ["A","B","C","D","E","F","G","H"]
        dest_row = int(index / 12)
        destination= f"{dest_list[dest_row]}{index + 1 - 12*(dest_row)}"
        output_design = {
            'name': "",
            'plate':"dest_01",
            'well': destination,
            'volume': 0,
            'note': None
        }
        protocol = f"\n\n    # Assembly design {index + 1}"
        # Extracting data from sources with designs
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']
            output_design['name'] += name + "/"
            output_design['volume'] += vol
            output_design[k] = name

            try:
                plate, well = find_source_well(sources_ot2, name, vol)
            except ValueError as e:
                # st.error(f"{name} need more volume")
                total_need = 0
                for design in designs:
                    for k, item in enumerate(design):
                        if item['name'] == name:
                            total_need += item['volume']
                total_have = sources.loc[sources['name'] == name, 'volume'].sum()
                st.error(f"total {total_have}ul in sources when {total_need}ul need")
                volume_error = True
                break

            protocol += f"""
    p300.pick_up_tip()
    p300.aspirate({vol}, {plate}['{well}'])  # {name}
    p300.dispense({vol}, destination['{destination}'])
    p300.drop_tip()
    """
        output_design['name'] = output_design['name'][:-1]  # Delete last "/"
        output_designs = pd.concat([output_designs, pd.DataFrame([output_design])])
        protocol_script += protocol

    return protocol_script, output_designs


def generate_janus_protocol(sources_janus, designs, destination_name, sources):
    protocol_rows = pd.DataFrame(columns=["Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"])
    output_rows = pd.DataFrame(columns=["name","plate","well","volume","note"])
    volume_error = False
    for index, design in enumerate(designs):
        if volume_error:
            protocol_rows, output_rows = None, None
            break
        
        # set target destination well
        dest_list = ["A","B","C","D","E","F","G","H"]
        dest_row = int(index / 12)
        destination = f"{dest_list[dest_row]}{index + 1 - 12*(dest_row)}"
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
                # st.write(sources_janus, name)
                plate, well = find_source_well(sources_janus, name, vol)
            except ValueError as e:
                total_need = 0
                for design in designs:
                    for k, item in enumerate(design):
                        if item['name'] == name:
                            total_need += item['volume']
                total_have = sources.loc[sources['name'] == name, 'volume'].sum()
                st.error(f"total {total_have}ul in sources when {total_need}ul need")
                volume_error = True
                break

            protocol_row["Asp.Rack"] = plate
            protocol_row["Asp.Posi"] = well
            protocol_row["Note"] = name
            protocol_row["Volume"] = vol
            
            output_row['note'] += f"{name}/"
            output_row['volume'] += vol
            output_row[k] = name

            protocol_rows = pd.concat([protocol_rows, pd.DataFrame([protocol_row])])
        output_row['note'] = output_row['note'][:-1]
        output_rows = pd.concat([output_rows,  pd.DataFrame([output_row])])

    return protocol_rows, output_rows



####################################################################################
####################################################################################

uploaded_file = st.file_uploader("Upload your Stocking Plate Excel file", type="xlsx")

if uploaded_file != None:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    default_vol = st.number_input("default volume", value = 100, min_value = 0, step = 10)
    sources = pd.DataFrame(columns = ["name","plate", "well", "volume","note"])

    for sheet_name in sheet_names:
        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        for row_index in range(len(df_sheet)):
            for col_index in range(len(df_sheet.columns)):
                cell_value = df_sheet.iloc[row_index, col_index]
                if pd.notna(cell_value) and cell_value == 'A':  # Detect row starting with 'A'
                    sr, sc = (row_index, col_index)

        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=sr, index_col=sc)
        
        for row_index, row in df_sheet.iterrows():
            for col_index, item in row.items():
                if pd.notna(item):
                    data = {
                        "name":item,
                        "plate":sheet_name.replace(" ", "_"),
                        "well":"".join([row_index, str(col_index)]),
                        "volume":default_vol,
                        "note":None
                    }
                    
                    sources = pd.concat([sources, pd.DataFrame([data])])

    sources = sources.assign(type = sources['name'].apply(lambda x:
        'Promoter' if x.startswith('(P)') else
        'CDS' if x.startswith('(C)') else
        'Connector' if x.startswith('(N)') else
        'Terminator' if x.startswith('(T)') else
        None))
        
    st.dataframe(sources)
    
    st.write("")
    st.write("")
    st.write("")
    st.subheader("Assembly Design")


    # 공통으로 넣을 거
    st.write("### volumes", unsafe_allow_html=True)
    others = sources[sources['type'].isna()]['name'].drop_duplicates().tolist()

    commons = []
    if "commons_row" not in st.session_state:
        st.session_state.commons_row = 1  # 초기 행 수 설정

    col1, col2, col3 = st.columns([3, 1, 7])
    with col1: st.write("Common parts")
    with col2: 
        if st.button('add'):
            st.session_state.commons_row = st.session_state.commons_row+ 1
    with col3: 
        if st.button('del') and st.session_state.commons_row> 1:
            st.session_state.commons_row = st.session_state.commons_row - 1

    for row in range(st.session_state.commons_row):
        col1, col2 = st.columns([6, 2])
        with col1:
            selected_name = st.selectbox(label="name", options=others, key=f"select_{row}", label_visibility="collapsed")
        with col2:
            volume = st.number_input(label="vol", value=10, step = 10, key=f"volume_{row}", label_visibility="collapsed")
        commons.append({'name':selected_name, 'volume':volume})

    ## 
    cols = 4 
    ## volumes input
    vols = []
    cols_placeholder = st.columns(cols)
    for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
        with cols_placeholder[col]:
            vols.append(st.number_input(label = category, value = 10, step = 10, min_value = 0, key=f"vols_{col}"))


    ## 그냥 똑같은 디자인 여러개 추가하는 게 나을듯?
    st.write("======================")
    total_vol = 0
    for common in commons:
        total_vol += common['volume']
    for vol in vols:
        total_vol += vol
    st.write(f"total {total_vol}ul of each assembly")
    st.write("======================")

    assembly_set_col = st.columns(2)
    with assembly_set_col[0]:
        rows = st.number_input(label="Number of assembly", value=3, min_value=1)
    with assembly_set_col[1]:
        repeats = st.number_input(label="Repeats of each assembly", value = 1, min_value = 1, step = 1)
    ## category naming
    cols_placeholder = st.columns(cols)
    for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
        with cols_placeholder[col]:
            st.write(category)
    
    designs = []

    connector_ex = sources[sources['name'].str.startswith('(N)s', na=False) | sources['name'].str.endswith('e', na=False)]['name'].drop_duplicates().sort_values().tolist()
    connector_ex = sorted(connector_ex, key = lambda x:[0 if c.isalpha() else 1 for c in x])
    connector_endo = sources[(~sources['name'].isin(connector_ex)) & sources['name'].str.startswith('(N)', na=False)]['name'].drop_duplicates().sort_values().tolist()
    connector_options = connector_ex + connector_endo

    # select box 생성
    options = {
        "Promoter": sources[sources['type'] == "Promoter"]['name'].drop_duplicates().tolist(),
        "CDS": sources[sources['type'] == "CDS"]['name'].drop_duplicates().tolist(),
        "Terminator": sources[sources['type'] == "Terminator"]['name'].drop_duplicates().tolist(),
        "Connector": connector_options
    }

    for row in range(rows):
        cols_placeholder = st.columns(cols)

        selected_items = {}
        for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
            with cols_placeholder[col]:
                if category == "Connector":
                    items = options[category]
                    selected_items[category] = [st.selectbox(
                        category,
                        items,
                        key = f"select_{row}_{col}",
                        index = (
                            connector_options.index(connector_ex[0]) if row == 0   # first row
                            else connector_options.index(connector_ex[row]) if row == rows - 1 # last row
                            else connector_options.index(connector_endo[row-1])  # else
                        ),
                        label_visibility="collapsed",
                        disabled = True
                    )]

                else:
                    items = options[category]
                    selected_items[category] = st.multiselect(
                        category,
                        items,
                        key=f"select_{row}_{col}",
                        # default=[items[0]] if items else [],
                        label_visibility="collapsed",
                    )
        selected_items_comb = product(
            selected_items["Promoter"],
            selected_items["CDS"],
            selected_items["Terminator"],
            selected_items["Connector"]
        )

        for combi in selected_items_comb:
            row_design = []
            for col, (category, item) in enumerate(zip(["Promoter", "CDS", "Terminator", "Connector"], combi)):
                row_design.append({'name': item, 'volume': vols[col]})
            row_design = row_design + commons
            for repeat in range(repeats):
                designs.append(row_design)




    ########################################################################################################
    ########################################################################################################
    st.write(sources)
    sources_ot2 = sources.copy()
    sources_janus = sources.copy()
    ### OT2 protocol
    with st.expander("OT2 protocol"):
        metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label = "Metadata").replace("\n", "\n    ")
        requirements = st.text_area(value = '"robotType": "OT-2", "apiLevel": "2.17"', label = "Requirements")

        plate_posit = []
        for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
            position = st.selectbox(options = range(1,12), label = f"{plate} position:", index = i)
            plate_posit.append([plate, position])
        plate_posit.append(["destination", st.selectbox(options = range(1,12), label = "destination_rack position:", index = i+1)])
        plate_posit.append(["tiprack", st.selectbox(options = range(1,12), label = "tibrack position:", index = i+2)])

        # OT-2 프로토콜 생성 함수
        protocol_code, lv1_outputs = generate_ot2_protocol(sources_ot2 , designs, plate_posit, metadata, requirements, sources)

        st.write("generated protocol:")
        st.code(protocol_code, language='python')
        st.write("generated output plate:")
        st.write(lv1_outputs)

    ### janus protocol
    with st.expander("Janus protocol"):
        dplate1_name = st.text_input("destination_name", value = "dest_01")
        protocol, lv1_outputs_janus = generate_janus_protocol(sources_janus, designs, dplate1_name, sources)
        st.write("generated protocol:")
        st.write(protocol)
        st.write("generated output plate:")
        st.write(lv1_outputs_janus)
    

    ########################################################################################################
    ########################################################################################################

    st.write("output plate ( OT2 protocol 기준, 별 차이는 없는데 이름 수정하면서 같이 수정할 예정 )")
    st.write(lv1_outputs)
    for i in range(7):
        st.write("")


    ### level2 designs
    st.subheader("Lv2 Design")
    def custom_sort_key(x):
        x = x.replace('(N)', '')  # '(N)' 제거
        return (0, 0) if x == 's|1' else (2, int(x.split('|')[0])) if '|e' in x else (1, int(x.split('|')[0]))

    # lv1_outputs에서 중복 제거
    unique_df = lv1_outputs.drop_duplicates(subset="name").sort_values(by=3, key=lambda x:x.map(custom_sort_key))

    # 3번 열(Connector 기준)으로 그룹화
    grouped = unique_df.groupby(3)

    # 그룹별 데이터를 딕셔너리 리스트로 변환
    grouped_data = [group.to_dict("records") for _, group in grouped]
    # 모든 가능한 조합 생성
    all_combinations = list(product(*grouped_data))

    # 중복 제거 조건을 만족하는 조합 필터링
    valid_combinations = []
    for combination in all_combinations:
        unique_1_values = {item[0] for item in combination}
        if len(unique_1_values) == len(combination):  # 중복이 없을 경우
            valid_combinations.append(combination)

    lv2_asp_vol = st.number_input("volume for each", value = 8)
    # lv2_designs 생성
    lv2_designs = []
    for combi in valid_combinations:
        row_design = []
        for item in combi:
            row_design.append({'name': item['name'], 'volume': lv2_asp_vol})
        lv2_designs.append(row_design)

    # 결과
    dplate2_name = st.text_input("destination 2 plate name", value = "dest2")

    # sources, designs, plate_posit, metadata, requirements
    janus_mapping, janus_output = generate_janus_protocol(lv1_outputs, lv2_designs, dplate2_name, lv1_outputs)
    st.write(janus_mapping)

