import streamlit as st
import pandas as pd
from itertools import product, permutations, combinations
import re

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

def generate_ot2_protocol(designs, plate_posit, metadata, requirements, sources):
    output_designs = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    protocol_script = f"""
from opentrons import protocol_api
from itertools import permutations

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
    group_counters = {}  # 그룹별 인덱스 초기화

    for index, design in enumerate(designs):
        if volume_error:
            protocol_script = "error"
            output_designs = pd.DataFrame()
            break

        # 목적지 웰 설정
        dest_list = ["A", "B", "C", "D", "E", "F", "G", "H"]
        dest_row = int(index / 12)
        destination = f"{dest_list[dest_row]}{index + 1 - 12 * (dest_row)}"
        
        # 디자인에 그룹 이름을 포함하여 이름 설정
        group_name = design[0]['note']  # 첫 번째 아이템의 note에서 그룹 이름 가져오기
        if group_name not in group_counters:
            group_counters[group_name] = 1  # 새로운 그룹이면 인덱스 초기화
        else:
            group_counters[group_name] += 1  # 기존 그룹이면 인덱스 증가

        output_design = {
            'name': f"{design[0]["name"]}-{design[1]["name"]}-{design[2]["name"]}-{design[3]["name"]}",
            'plate': "dest_01",
            'well': destination,
            'volume': 0,
            'note': f"{group_name}_{group_counters[group_name]}"
        }
        protocol = f"\n\n    # Assembly design {index + 1}"

        # 디자인에서 소스 데이터 추출
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']
            output_design['volume'] += vol
            output_design[k] = name

            try:
                plate, well = find_source_well(sources, name, vol)
            except ValueError:
                total_have = sources.loc[sources['name'] == name, 'volume'].sum()
                total_need = sum(item['volume'] for design in designs for item in design if item['name'] == name)
                st.error(f"total {total_have}ul in sources when {total_need}ul need")
                volume_error = True
                break

            protocol += f"""
    p300.pick_up_tip()
    p300.aspirate({vol}, {plate}['{well}'])  # {name}
    p300.dispense({vol}, destination['{destination}'])
    p300.drop_tip()
    """
        output_designs = pd.concat([output_designs, pd.DataFrame([output_design])])
        protocol_script += protocol

    return protocol_script, output_designs

def generate_janus_protocol(designs, destination_name, sources, naming = "TU"):
    protocol_rows = pd.DataFrame(columns=["Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"])
    output_rows = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    volume_error = False
    group_counters = {}  # 그룹별 인덱스 초기화
    for index, design in enumerate(designs):
        if volume_error:
            protocol_rows, output_rows = None, None
            break
        plate_num = int((index)/96)
        dest_name = destination_name[plate_num]
        plate_index = index - plate_num*96 + 1
        # 목적지 웰 설정
        dest_list = ["A", "B", "C", "D", "E", "F", "G", "H"]
        dest_row = int((plate_index-0.5)//12)
        # st.write(f"plate_num={plate_num}, dest_name={dest_name}, plate_index={plate_index},dest_row={dest_row}")

        destination = f"{dest_list[dest_row]}{plate_index - 12 * (dest_row)}"
        
        # 디자인에 그룹 이름을 포함하여 이름 설정
        group_name = design[0]['note']  # 첫 번째 아이템의 note에서 그룹 이름 가져오기
        if group_name not in group_counters:
            group_counters[group_name] = 1  # 새로운 그룹이면 인덱스 초기화
        else:
            group_counters[group_name] += 1  # 기존 그룹이면 인덱스 증가

        protocol_row = {
            "Component": f"{group_name}_{group_counters[group_name]}",
            "Asp.Rack": "",
            "Asp.Posi": "",
            "Dsp.Rack": dest_name,
            "Dsp.Posi": destination,
            "Volume": 0,
            "Note": group_name
        }

        output_row = {
            "name": f"{design[0]["name"]}-{design[1]["name"]}-{design[2]["name"]}-{design[3]["name"]}" if naming == "TU" else f"{group_name}_{group_counters[group_name]}",
            "plate": dest_name,
            "well": destination,
            "volume": 0,
            "note": f"{group_name}_{group_counters[group_name]}"
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


if 'total_mk' not in st.session_state:
    st.session_state.total_mk = 0
if 'design2_len' not in st.session_state:
    st.session_state.design2_len = 0
if "commons_row" not in st.session_state:
    st.session_state.commons_row = 1  # 초기 행 수 설정
if "commons_row2" not in st.session_state:
    st.session_state.commons_row2 = 1  # 초기 행 수 설정


# 파일 업로드 및 데이터 처리
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
        default_vol = st.number_input("Default volume", value=100, min_value=0, step=10, label_visibility="collapsed")

    sources = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])

    for i, sheet_name in enumerate(sheet_names):
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
                        "plate": plate_names[i].replace(" ", "_"),  # 사용자가 입력한 plate_name 사용
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
    with st.expander("Sourceplate"):
        for plate_name, group in sources.groupby('plate'):
            st.subheader(f"Plate: {plate_name}")
            st.dataframe(group)

    sources_org = sources.copy()

    st.write("")
    st.write("")
    st.write("")
    st.write("## Assembly Design")

    st.write("### Lv1 Design")
    
    st.write("> #### Groups")
    # 사용자에게 그룹 지정 옵션 제공
    user_defined_groups = []
    user_defined_groups_nop = []
    user_defined_groups_roa = []

    # 사용자 정의 그룹 수 입력을 한 줄에 배치
    group_col1, group_col2 = st.columns([2, 8])
    with group_col1:
        st.write("* Number of groups")
    with group_col2:
        num_groups = st.number_input("Number of groups", min_value=1, value=1, step=1, label_visibility="collapsed")

    # 각 그룹에 대해 사용자로부터 입력받기
    group_col1, group_col2, group_col3, group_col4 = st.columns([2, 3, 2, 2])
    with group_col2:
        st.write("Group names")
    with group_col3:
        st.write("Number of TU")
    with group_col4:
        st.write("Repeats of assembly")

    for i in range(num_groups):
        group_col1, group_col2, group_col3, group_col4 = st.columns([2, 3, 2, 2])
        with group_col1:
            st.write(f"* Group {i+1}")
        with group_col2:
            group_name = st.text_input(f"Group {i+1} Name", value=f"Group_{i+1}", key=f"group_name_{i}", label_visibility="collapsed")
            user_defined_groups.append(group_name)
        with group_col3:
            group_nop = st.number_input(f"Number of TU", value = 3, key = f"Group_noa{i}", min_value = 1, step = 1, label_visibility = "collapsed")
            user_defined_groups_nop.append(group_nop)
        with group_col4:
            group_roa = st.number_input(f"Repeats of assembly", value = 1, key = f"Group_roa{i}", min_value = 1, step = 1, label_visibility = "collapsed", disabled=True)
            user_defined_groups_roa.append(group_roa)

    # TU designs
    st.write("> #### TU design")
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
                    if category == "Connector":
                        items = options[category]
                        selected_items[category] = [st.selectbox(
                            category,
                            items,
                            key=f"select_{row}_{col}_{g}",
                            index=(
                                connector_options.index(connector_ex[0]) if row == 0   # 첫 번째 행
                                else connector_options.index(connector_ex[row]) if row == rows - 1 # 마지막 행
                                else connector_options.index(connector_endo[row-1])  # 그 외
                            ),
                            label_visibility="collapsed",
                            disabled=True
                        )]

                    else:
                        items = options[category]
                        selected_items[category] = st.multiselect(
                            category,
                            items,
                            key=f"select_{row}_{col}_{g}",
                            label_visibility="collapsed",
                            max_selections= 1 if category == "CDS" else None
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
    # Group by the relevant columns and sum the 'tu_usage' column
    design_df = design_df.groupby(["Promoter", "CDS", "Terminator", "Connector"]).agg({
        "Group": "first",
        "tu_usage": "sum"
    }).reset_index()
    st.warning(f"{len(design_df)} of TU, {len(design2_list)} of Lv2 design")
    # st.write(design_df)
    # st.write(design2_list)




    ### 세부사항 조정
    if st.button("Apply", key="apply_button"):
        st.session_state.apply_clicked = True

    if st.session_state.get("apply_clicked", False):

        st.write("> #### Volume setting")

        # 공통 부품 추가
        others = sources[sources['type'].isna()]['name'].drop_duplicates().tolist()

        commons = []


        col1, col2, col3 = st.columns([2, 1, 8])
        with col1: st.write("Common parts")
        with col2: 
            if st.button('add'):
                st.session_state.commons_row += 1
        with col3: 
            if st.button('del') and st.session_state.commons_row > 1:
                st.session_state.commons_row -= 1
        col1, col2, col3, col4 = st.columns([3,2,2,2])
        with col1: st.write("Part name")
        with col2: st.write("Volume (ul)")
        with col3: st.write("Stock plate")
        with col4: st.write("Stock location (Well)")
        for row in range(st.session_state.commons_row):
            col1, col2, col3, col4 = st.columns([3,2,2,2])
            with col1:
                selected_name = st.text_input(label="name", key=f"selectname_{row}", label_visibility="collapsed", value= "GGAmixture")
                name_exist = selected_name in sources['name'].values
            with col2:
                volume = st.number_input(label="vol", value=2., step=0.1, min_value = 0., key=f"volume_{row}", label_visibility="collapsed")
            with col3:
                stock_plate = st.text_input(label="source plate", key = f"common_source_plate_{row}", label_visibility = "collapsed", value = "", disabled = name_exist)
            with col4:
                stock_code = st.text_input(label="stock location", key = f"common_stock_location_{row}", label_visibility = "collapsed", value = "", disabled = name_exist)
            commons.append({'name': selected_name, 'volume': volume})

            ## 이거 source에 있으면 deadvolume 추가해서 계산할 것.
            reqvol = design_df['tu_usage'].sum()*volume
            
            # Create a DataFrame for the common part and add it to sources
            common_data = pd.DataFrame([{
                'name': selected_name,
                'plate': stock_plate,
                'well': stock_code,
                'volume': reqvol+2, 
                'note': 'common'
            }])

            if selected_name in sources['name'].values:
                current_vol = sources.loc[sources['name'] == selected_name, ['volume']].values.sum()
                if current_vol > reqvol:
                    st.success(f"total {reqvol}ul of {selected_name} required while {current_vol} in sources")
                else:
                    st.error(f"total {reqvol}ul of {selected_name} required while {current_vol} in sources")
            else:
                if stock_plate.strip() == "" or not re.match(r'^[A-Ha-h][1-9]$|^[A-Ha-h]1[0-2]$', stock_code):
                    st.error(f"Please insert correct Stock plate and Stock location \n ex) Stock_plate3, A7")
                else:
                    st.warning(f"total {reqvol}ul of {selected_name} required in {stock_plate}, {stock_code}")
                    sources = pd.concat([sources, common_data], ignore_index=True)


        # 볼륨 입력
        st.write("TU parts")
        vols = []
        cols_placeholder = st.columns(cols)
        for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
            with cols_placeholder[col]:
                vols.append(st.number_input(label=category, value=2., step=0.1, min_value=0., key=f"vols_{col}"))

        # 총 볼륨 계산
        total_vol = sum(common['volume'] for common in commons) + sum(vols)
        st.success(f"total {total_vol}ul of each TU")

        for _ in range(2):
            st.write("")


        ## lv2 Design
        st.write("### Lv2 Design")

        st.write("> Volume for each TU (*Deadvolume)")
        col1, col2 = st.columns([7,2])
        with col1:
            lv2_volume = st.number_input(label = "Lv2 volume for each TU", min_value = 0., value = 8., step = 0.1, label_visibility="collapsed")
        with col2:
            lv2_deadvol = st.number_input(label = "Dead volume for each TU", min_value = 0., value = 2., step = 0.1, label_visibility="collapsed")

        lv2_commons = []

        col1, col2, col3 = st.columns([2, 1, 8])
        with col1: st.write("> Common parts")
        with col2: 
            if st.button('add', key = "add2"):
                st.session_state.commons_row2 += 1
        with col3: 
            if st.button('del', key = "del2") and st.session_state.commons_row2 > 1:
                st.session_state.commons_row2 -= 1

        col1, col2, col3, col4 = st.columns([3,2,2,2])
        with col1: st.write("Part name")
        with col2: st.write("Volume (ul)")
        with col3: st.write("Stock plate")
        with col4: st.write("Stock location")
        for row in range(st.session_state.commons_row2):
            col1, col2, col3, col4 = st.columns([3,2,2,2])
            with col1:
                selected_name = st.text_input(label="name", key=f"selectname2_{row}", label_visibility="collapsed", value= "Vector")
            with col2:
                volume = st.number_input(label="vol", value=10., step=0.1, min_value = 0., key=f"volume2_{row}", label_visibility="collapsed")
            with col3:
                stock_plate = st.text_input(label="source plate", key = f"common2_source_plate_{row}", label_visibility = "collapsed", value = "Stockplate2")
            with col4:
                stock_code = st.text_input(label="stock location", key = f"common2_stock_location_{row}", label_visibility = "collapsed", value = "A2")
            lv2_commons.append({'name': selected_name, 'volume': volume})
            
            reqvol = len(design2_list)*volume
            
            common_data = pd.DataFrame([{
                'name': selected_name,
                'plate': stock_plate,
                'well': stock_code,
                'volume': reqvol*volume,
                'note': 'common'
            }])
            
            if selected_name in sources['name'].values:
                current_vol = sources.loc[sources['name'] == selected_name, ['volume']].values.sum()
                if current_vol > reqvol:
                    st.success(f"total {reqvol}ul of {selected_name} required while {current_vol} in sources")
                else:
                    st.error(f"total {reqvol}ul of {selected_name} required while {current_vol} in sources")
            else:
                if stock_plate.strip() == "" or not re.match(r'^[A-Ha-h][1-9]$|^[A-Ha-h]1[0-2]$', stock_code):
                    st.error(f"Please insert correct Stock plate and Stock location \n ex) Stock_plate3, A7")
                else:
                    st.warning(f"total {reqvol}ul of {selected_name} required in {stock_plate}, {stock_code}")
                    sources = pd.concat([sources, common_data], ignore_index=True)
            
            sources = pd.concat([sources, common_data], ignore_index=True)

            for common in lv2_commons:
                if lv2_volume*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons) > 50:
                    st.warning(f"Total volume({lv2_volume*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons)}ul) is too high(>50ul)!")


        # Convert DataFrame to designs format

        # st.write(design_df)
        designs = []
        for _, row in design_df.iterrows():
            # pass
            row_volume = sum(vols[col] * row["tu_usage"] for col in range(4)) + sum(common['volume'] * row["tu_usage"] for common in commons)
            ## 몇개를 해야 하는지..
            row_repeat = int((row_volume-0.5)/(50-lv2_deadvol)) + 1
            # st.write(row)
            for i in range(row_repeat):
                row_design = []
                for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):
                    if row[category] != "":
                        row_design.append({'name': row[category], 'volume': vols[col]*row["tu_usage"]/row_repeat})
                for common in commons:
                    common_a = {'name': common['name'], 'volume': common['volume'] * row["tu_usage"]/row_repeat}
                    row_design += [common_a]
                for repeat in range(user_defined_groups_roa[row["Group"]]):
                    design_with_note = [{'name': item['name'], 'volume': item['volume'], 'note': row["Group"]} for item in row_design]
                    designs.append(design_with_note)



        designs_plate_num = int((len(designs)-0.5)/96)+1

        # for i in range(3):
        #     st.write("")

        # with st.expander("Design details"):
        #     st.write(designs)
        
        for i in range(10):
            st.write("")

        #####################################################################################################

        st.write("## Outputs")
        st.write("#### Lv1")
        # with st.expander("Design detail for lv1"):
        #     st.dataframe(design_df)
        #     st.write("Total TU useage: ", sum(design_df['tu_usage']))

        ### LV1 protocol generate
        device = st.selectbox(label = "Lv1 Device", options = ["OT2", "Janus"], key='device')
        # OT2 프로토콜 생성
        if device == "OT2":
            plate_len = int((len(designs)-0.5)/96+1)
            if plate_len > 1:
                st.error("OT2 does not support multiple destinations yet..\nPlease use Janus protocol")
            else:
                with st.expander("OT2 protocol"):
                    metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label="Metadata").replace("\n", "\n    ")
                    requirements = st.text_area(value='"robotType": "OT-2", "apiLevel": "2.17"', label="Requirements")

                    plate_posit = []
                    for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
                        position = st.selectbox(options=range(1, 12), label=f"{plate} position:", index=i)
                        plate_posit.append([plate, position])
                    plate_posit.append(["destination", st.selectbox(options=range(1, 12), label="destination_rack position:", index=i+1)])
                    plate_posit.append(["tiprack", st.selectbox(options=range(1, 12), label="tibrack position:", index=i+2)])

                    protocol, lv1_outputs = generate_ot2_protocol(designs, plate_posit, metadata, requirements, sources)
                    
                    st.write("generated protocol:")
                    st.code(protocol, language='python')
                    st.write("generated output plate:")
                    st.write(lv1_outputs)
                    st.write("updated sources")
                    st.write(sources)
        # Janus 프로토콜 생성
        if device == "Janus":
            plate_len = int((len(designs)-0.5)/96+1)
            dplate1_name = []
            for i in range(plate_len):
                dplate1_name.append(st.text_input(f"Destination Plate {i+1} Name", value=f"destination_{i+1}", key = f"dplate{i}_name"))
            with st.expander("Janus protocol"):
                protocol, lv1_outputs = generate_janus_protocol(designs, dplate1_name, sources)
                st.write("generated mapping:")
                st.write(protocol)
                st.write("generated output plate:")
                st.write(lv1_outputs)
                st.write("updated sources")
                st.write(sources)
        for i in range(7):
            st.write("")


        ###################################################################################################
        st.write("### Lv2")

        designs2 = []
        
        for comb in design2_list: # group
            group, items = comb
            row_design = []
            for item in items:
                item_name = item['P']+"-"+item['C']+"-"+item['T']+"-"+item['N']
                volume = lv2_volume
                note = user_defined_groups[group]

                row_design.append({'name':item_name, 'volume':volume, 'note':note})
            #     name = n
            #     volume = lv2_volume
            #     note = user_defined_groups[group]
            row_design += lv2_commons
            designs2.append(row_design)

            #     row_design.append({'name': name, 'volume': volume, 'note':note})
            # row_design += lv2_commons
            # designs2.append(row_design)

        ###################################################################################################

        device2 = st.selectbox(label = "Lv1 Device", options = ["OT2", "Janus"], key='device2')

        # OT2 프로토콜 생성
        if device2 == "OT2":
            plate_len = int((len(designs)-0.5)/96+1)
            if plate_len > 1:
                st.error("OT2 does not support multiple destinations yet..\nPlease use Janus protocol")
            else:
                with st.expander("OT2 protocol"):
                    metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label="Metadata", key="meta2").replace("\n", "\n    ")
                    requirements = st.text_area(value='"robotType": "OT-2", "apiLevel": "2.17"', label="Requirements", key="req2")

                    plate_posit = []
                    for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
                        position = st.selectbox(options=range(1, 12), label=f"{plate} position:", key=f"pos2_{i}_{plate}")
                        plate_posit.append([plate, position])
                    plate_posit.append(["destination", st.selectbox(options=range(1, 12), label="destination_rack position:", index=i+1, key = "dest_pos2")])
                    plate_posit.append(["tiprack", st.selectbox(options=range(1, 12), label="tibrack position:", index=i+2, key = "tip_pos2")])

                    protocol, lv1_outputs = generate_ot2_protocol(designs, plate_posit, metadata, requirements, sources)
                    
                    st.write("generated protocol:")
                    st.code(protocol, language='python')
                    st.write("generated output plate:")
                    st.write(lv1_outputs)
                    st.write("updated sources")
                    st.write(sources)


        if device2 == 'Janus':
            ### janus mapping generate
            design2_plate_num = int((len(designs2)-0.5)/96)+1
            # st.session_state.design2_len = len(designs2)
            # st.write(design2_plate_num)
        
            dplate2_name = []
            for i in range(design2_plate_num):
                dplate2_name.append(st.text_input(label = f"Destination Plate Name {i+1}", value = f"Dest_02_{i+1}"))
            # Combine sources and lv1_outputs
            combined_sources = pd.concat([sources, lv1_outputs])
            # Generate Janus protocol for Lv2
            protocol2, lv2_outputs = generate_janus_protocol(designs2, dplate2_name, combined_sources, naming="note")
            # Separate sources and lv1_outputs
            sources = combined_sources[combined_sources['name'].isin(sources['name'])].iloc[:, :6]
            lv1_outputs = combined_sources[combined_sources['name'].isin(lv1_outputs['name'])]
            
            
            st.write("Janus mapping")
            st.write(protocol2.reset_index(drop=True))
            st.write("Final output plate")
            st.write(lv2_outputs.reset_index(drop=True))
            st.write("Updated Sources")
            st.write(sources)


            # debugging area
            # st.write(designs2)
