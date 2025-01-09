import streamlit as st
import pandas as pd
from itertools import product

# Streamlit 페이지 설정
st.set_page_config(layout="wide")

def find_source_well(sources_, name, required_volume):
    sources_row = sources_[(sources_['name'] == name) & (sources_['volume'] >= required_volume)]
    if sources_row.empty:
        st.warning(f"Not enough volume available for '{name}'")
        raise ValueError(f"Not enough volume available for '{name}'")
    row = sources_row.iloc[0]
    sources_.loc[(sources_['name'] == row['name']) & (sources_['plate'] == row['plate']) & (sources_['well'] == row['well']), 'volume'] -= required_volume
    return row['plate'], row['well']

def generate_ot2_protocol(sources_ot2, designs, plate_posit, metadata, requirements, sources):
    output_designs = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
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
    
    # Labware 위치 설정
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

        # 목적지 웰 설정
        dest_list = ["A", "B", "C", "D", "E", "F", "G", "H"]
        dest_row = int(index / 12)
        destination = f"{dest_list[dest_row]}{index + 1 - 12 * (dest_row)}"
        output_design = {
            'name': "",
            'plate': "dest_01",
            'well': destination,
            'volume': 0,
            'note': None
        }
        protocol = f"\n\n    # Assembly design {index + 1}"
        
        # 디자인에서 소스 데이터 추출
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']
            output_design['name'] += name + "/"
            output_design['volume'] += vol
            output_design[k] = name

            try:
                plate, well = find_source_well(sources_ot2, name, vol)
            except ValueError:
                total_need = sum(item['volume'] for design in designs for item in design if item['name'] == name)
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
        output_design['name'] = output_design['name'][:-1]  # 마지막 "/" 제거
        output_designs = pd.concat([output_designs, pd.DataFrame([output_design])])
        protocol_script += protocol

    return protocol_script, output_designs

def generate_janus_protocol(sources_janus, designs, destination_name, sources):
    protocol_rows = pd.DataFrame(columns=["Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"])
    output_rows = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    volume_error = False
    for index, design in enumerate(designs):
        if volume_error:
            protocol_rows, output_rows = None, None
            break
        
        # 목적지 웰 설정
        dest_list = ["A", "B", "C", "D", "E", "F", "G", "H"]
        dest_row = int(index / 12)
        destination = f"{dest_list[dest_row]}{index + 1 - 12 * (dest_row)}"
        protocol_row = {
            "Component": f"{destination_name}_{index + 1}",
            "Asp.Rack": "",
            "Asp.Posi": "",
            "Dsp.Rack": destination_name,
            "Dsp.Posi": destination,
            "Volume": 0,
            "Note": ""
        }
        output_row = {
            "name": f"{destination_name}_{index + 1}",
            "plate": destination_name,
            "well": destination,
            "volume": 0,
            "note": ""
        }
        
        # 디자인에서 소스 데이터 추출
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']

            try:
                plate, well = find_source_well(sources_janus, name, vol)
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
            
            output_row['note'] += f"{name}/"
            output_row['volume'] += vol
            output_row[k] = name

            protocol_rows = pd.concat([protocol_rows, pd.DataFrame([protocol_row])])
        output_row['note'] = output_row['note'][:-1]
        output_rows = pd.concat([output_rows, pd.DataFrame([output_row])])

    return protocol_rows, output_rows

# 파일 업로드 및 데이터 처리
uploaded_file = st.file_uploader("Upload your Stocking Plate Excel file", type="xlsx")
if uploaded_file is None:
    uploaded_file = "./plate_sample.xlsx"
if uploaded_file is not None:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    default_vol = st.number_input("default volume", value=100, min_value=0, step=10)
    sources = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])

    for sheet_name in sheet_names:
        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        for row_index in range(len(df_sheet)):
            for col_index in range(len(df_sheet.columns)):
                cell_value = df_sheet.iloc[row_index, col_index]
                if pd.notna(cell_value) and cell_value == 'A':  # 'A'로 시작하는 행 감지
                    sr, sc = (row_index, col_index)

        df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=sr, index_col=sc)

        for row_index, row in df_sheet.iterrows():
            for col_index, item in row.items():
                if pd.notna(item):
                    data = {
                        "name": item,
                        "plate": sheet_name.replace(" ", "_"),
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
    
    # 플레이트별로 데이터프레임 표시
    for plate_name, group in sources.groupby('plate'):
        st.subheader(f"Plate: {plate_name}")
        st.dataframe(group)

    st.write("")
    st.write("")
    st.write("")
    st.subheader("Assembly Design")

    # 공통 부품 추가
    st.write("### volumes", unsafe_allow_html=True)
    others = sources[sources['type'].isna()]['name'].drop_duplicates().tolist()

    commons = []
    if "commons_row" not in st.session_state:
        st.session_state.commons_row = 1  # 초기 행 수 설정

    col1, col2, col3 = st.columns([3, 1, 7])
    with col1: st.write("Common parts")
    with col2: 
        if st.button('add'):
            st.session_state.commons_row += 1
    with col3: 
        if st.button('del') and st.session_state.commons_row > 1:
            st.session_state.commons_row -= 1

    for row in range(st.session_state.commons_row):
        col1, col2 = st.columns([6, 2])
        with col1:
            selected_name = st.selectbox(label="name", options=others, key=f"select_{row}", label_visibility="collapsed")
        with col2:
            volume = st.number_input(label="vol", value=10, step=10, key=f"volume_{row}", label_visibility="collapsed")
        commons.append({'name': selected_name, 'volume': volume})

    # 볼륨 입력
    cols = 4 
    vols = []
    cols_placeholder = st.columns(cols)
    for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
        with cols_placeholder[col]:
            vols.append(st.number_input(label=category, value=10, step=10, min_value=0, key=f"vols_{col}"))

    # 총 볼륨 계산
    st.write("======================")
    total_vol = sum(common['volume'] for common in commons) + sum(vols)
    st.write(f"total {total_vol}ul of each assembly")
    st.write("======================")

    assembly_set_col = st.columns(2)
    with assembly_set_col[0]:
        rows = st.number_input(label="Number of assembly", value=3, min_value=1)
    with assembly_set_col[1]:
        repeats = st.number_input(label="Repeats of each assembly", value=1, min_value=1, step=1)

    # 카테고리 이름 설정
    cols_placeholder = st.columns(cols)
    for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
        with cols_placeholder[col]:
            st.write(category)
    
    designs = []

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
                        key=f"select_{row}_{col}",
                        index=(
                            connector_options.index(connector_ex[0]) if row == 0   # 첫 번째 행
                            else connector_options.index(connector_ex[row]) if row == rows - 1 # 마지막 행
                            else connector_options.index(connector_endo[row-1])  # 그 외
                        ),
                        label_visibility="collapsed",
                        disabled=False
                    )]

                else:
                    items = options[category]
                    selected_items[category] = st.multiselect(
                        category,
                        items,
                        key=f"select_{row}_{col}",
                        label_visibility="collapsed",
                    )
                    if not selected_items[category]:
                        selected_items[category] = [""]

        selected_items_comb = product(
            selected_items["Promoter"],
            selected_items["CDS"],
            selected_items["Terminator"],
            selected_items["Connector"]
        )

        for combi in selected_items_comb:
            row_design = []
            for col, (category, item) in enumerate(zip(["Promoter", "CDS", "Terminator", "Connector"], combi)):
                if item != "":
                    row_design.append({'name': item, 'volume': vols[col]})
            row_design += commons
            for repeat in range(repeats):
                designs.append(row_design)

    # OT2 프로토콜 생성
    sources_ot2 = sources.copy()
    sources_janus = sources.copy()
    with st.expander("OT2 protocol"):
        metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label="Metadata").replace("\n", "\n    ")
        requirements = st.text_area(value='"robotType": "OT-2", "apiLevel": "2.17"', label="Requirements")

        plate_posit = []
        for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
            position = st.selectbox(options=range(1, 12), label=f"{plate} position:", index=i)
            plate_posit.append([plate, position])
        plate_posit.append(["destination", st.selectbox(options=range(1, 12), label="destination_rack position:", index=i+1)])
        plate_posit.append(["tiprack", st.selectbox(options=range(1, 12), label="tibrack position:", index=i+2)])

        protocol_code, lv1_outputs = generate_ot2_protocol(sources_ot2, designs, plate_posit, metadata, requirements, sources)

        st.write("generated protocol:")
        st.code(protocol_code, language='python')
        st.write("generated output plate:")
        st.write(lv1_outputs)

    # Janus 프로토콜 생성
    with st.expander("Janus protocol"):
        dplate1_name = st.text_input("destination_name", value="dest_01")
        protocol, lv1_outputs_janus = generate_janus_protocol(sources_janus, designs, dplate1_name, sources)
        st.write("generated protocol:")
        st.write(protocol)
        st.write("generated output plate:")
        st.write(lv1_outputs_janus)

    st.write(lv1_outputs)
    for i in range(7):
        st.write("")

    # 레벨 2 디자인
    st.subheader("Lv2 Design")

    # 사용자에게 그룹 지정 옵션 제공
    group_options = lv1_outputs['name'].unique().tolist()
    user_defined_groups = []

    # 사용자 정의 그룹 수 입력
    num_groups = st.number_input("Number of groups", min_value=1, value=1, step=1)

    # 각 그룹에 대해 사용자로부터 입력받기
    for i in range(num_groups):
        group_name = st.text_input(f"Group {i+1} Name", value=f"Group_{i+1}")
        selected_items = st.multiselect(f"Select items for {group_name}", options=group_options, key=f"group_{i}")
        user_defined_groups.append((group_name, selected_items))

    # Lv2 디자인에 공통 부품 추가
    st.write("### Common parts for Lv2", unsafe_allow_html=True)
    lv2_commons = []
    if "lv2_commons_row" not in st.session_state:
        st.session_state.lv2_commons_row = 1  # 초기 행 수 설정

    col1, col2, col3 = st.columns([3, 1, 7])
    with col1: st.write("Common parts")
    with col2: 
        if st.button('add', key='lv2_add'):
            st.session_state.lv2_commons_row += 1
    with col3: 
        if st.button('del', key='lv2_del') and st.session_state.lv2_commons_row > 1:
            st.session_state.lv2_commons_row -= 1

    for row in range(st.session_state.lv2_commons_row):
        col1, col2 = st.columns([6, 2])
        with col1:
            selected_name = st.selectbox(label="name", options=others, key=f"lv2_select_{row}", label_visibility="collapsed")
        with col2:
            volume = st.number_input(label="vol", value=10, step=10, key=f"lv2_volume_{row}", label_visibility="collapsed")
        lv2_commons.append({'name': selected_name, 'volume': volume})

    if st.button("Generate Lv2 Designs"):
        valid_combinations = []

        # 사용자 정의 그룹 내에서 가능한 조합 생성
        for group_name, items in user_defined_groups:
            group_data = lv1_outputs[lv1_outputs['name'].isin(items)].to_dict("records")
            group_combinations = list(product(group_data, repeat=1))  # 각 그룹 내에서 조합 생성
            for combination in group_combinations:
                unique_1_values = {item['name'] for item in combination}
                if len(unique_1_values) == len(combination):  # 중복이 없을 경우
                    valid_combinations.append(combination)

        lv2_asp_vol = st.number_input("Volume for each", value=8)

        # lv2_designs 생성
        lv2_designs = []
        for combi in valid_combinations:
            row_design = [{'name': item['name'], 'volume': lv2_asp_vol} for item in combi]
            row_design += lv2_commons  # 공통 부품 추가
            lv2_designs.append(row_design)

        # lv1_outputs에 sources 추가
        combined_sources = pd.concat([lv1_outputs, sources])

        st.write(combined_sources)

        # 결과 출력
        dplate2_name = st.text_input("Destination 2 plate name", value="dest2")
        janus_mapping, janus_output = generate_janus_protocol(combined_sources, lv2_designs, dplate2_name, combined_sources)
        st.write(janus_mapping)
