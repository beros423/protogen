import streamlit as st
import pandas as pd
from itertools import product
import math
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
            "Component": f"{naming}_{group_name}_{group_counters[group_name]}",
            "Asp.Rack": "",
            "Asp.Posi": "",
            "Dsp.Rack": dest_name,
            "Dsp.Posi": destination,
            "Volume": 0,
            "Note": group_name
        }

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


if "commons_row" not in st.session_state:
    st.session_state.commons_row = 1  # 초기 행 수 설정
if "commons_row2" not in st.session_state:
    st.session_state.commons_row2 = 1  # 초기 행 수 설정


st.title("Assembly Design Tool")
st.write("This tool is designed to assist in the assembly design process for synthetic biology projects. It allows users to upload an Excel file containing information about parts and their respective volumes, and then generates assembly designs based on user-defined parameters.")
st.write(">## Input")
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
        default_vol = st.number_input("Default volume", value=10000, min_value=0, step=10, label_visibility="collapsed")

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

    st.write("### Groups")
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
    # others = sources[sources['type'].isna()]['name'].drop_duplicates().tolist()
    commons = []
    col1, col2, col3 = st.columns([3, 1, 8])
    with col1: st.write("### Lv1 Common parts")
    st.write('''Set the parts to be included in every Lv1 TU. Specify the plate name and location.  
             (If the part name exists in the source, that source will be used.)
             ''')
    with col2: 
        if st.button('add'):
            st.session_state.commons_row += 1
    with col3: 
        if st.button('del') and st.session_state.commons_row > 0:
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
            stock_plate = st.text_input(label="source plate", key = f"common_source_plate_{row}", label_visibility = "collapsed", value = "GGAmix_plate", disabled = name_exist)
        with col4:
            stock_code = st.text_input(label="stock location", key = f"common_stock_location_{row}", label_visibility = "collapsed", value = "A1", disabled = name_exist)
        commons.append({'name': selected_name, 'volume': volume, 'in_source': name_exist, 'plate': stock_plate, 'well': stock_code})

        if selected_name in sources['name'].values:
            current_vol = sources.loc[sources['name'] == selected_name, ['volume']].values.sum()
            st.success(f"{selected_name} detected {current_vol} in sources")
        elif validate_stock_location(stock_plate, stock_code):
            st.warning(f"Please ensure {selected_name} is available in {stock_plate}, {stock_code}")
        else:
            st.error("Invalid Stock plate or Stock location format. Example) Stock_plate3, A7")

    for i in range(3):
        st.write("")
    
    # 총 볼륨 계산
    total_vol = sum(common['volume'] for common in commons) + sum(vols)
    st.success(f"total {total_vol}ul of each TU")
    # st.session_state.total_vol = total_vol

    for i in range(5):
        st.write("")

    ## lv2 commons
    lv2_commons = []
    col1, col2, col3 = st.columns([3, 1, 8])
    with col1: st.write("### Lv2 Common parts")
    with col2: 
        if st.button('add', key = "add2"):
            st.session_state.commons_row2 += 1
    with col3: 
        if st.button('del', key = "del2") and st.session_state.commons_row2 > 0:
            st.session_state.commons_row2 -= 1
    st.write('''Set the parts to be included in every Lv2 outputs. Specify the plate name and location.  
             (If the part name exists in the provided source, it will be used.)''')

    col1, col2, col3, col4 = st.columns([3,2,2,2])
    with col1: st.write("Part name")
    with col2: st.write("Volume (ul)")
    with col3: st.write("Stock plate")
    with col4: st.write("Stock location")
    for row in range(st.session_state.commons_row2):
        col1, col2, col3, col4 = st.columns([3,2,2,2])
        with col1:
            selected_name = st.text_input(label="name", key=f"selectname2_{row}", label_visibility="collapsed", value= "Vector")
            name_exist = selected_name in sources['name'].values
        with col2:
            volume = st.number_input(label="vol", value=10., step=0.1, min_value = 0., key=f"volume2_{row}", label_visibility="collapsed")
        with col3:
            stock_plate = st.text_input(label="source plate", key = f"common2_source_plate_{row}", label_visibility = "collapsed", value = "Vector_plate", disabled=name_exist)
        with col4:
            stock_code = st.text_input(label="stock location", key = f"common2_stock_location_{row}", label_visibility = "collapsed", value = "A1", disabled=name_exist)
        lv2_commons.append({'name': selected_name, 'volume': volume, 'in_source': name_exist, 'plate': stock_plate, 'well': stock_code})
        
        for common in lv2_commons:
            if total_vol*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons) > lv1_maxvol:
                st.warning(f"Warning: Total volume({total_vol*max(user_defined_groups_nop)+sum(item['volume'] for item in lv2_commons)}ul) is too high(>{lv1_maxvol})!")
        
        if selected_name in sources['name'].values:
            current_vol = sources.loc[sources['name'] == selected_name, ['volume']].values.sum()
            st.success(f"{selected_name} detected {current_vol} in sources")
        elif validate_stock_location(stock_plate, stock_code):
            st.warning(f"Please ensure {selected_name} is available in {stock_plate}, {stock_code}")
        else:
            st.error("Invalid Stock plate or Stock location format. Example) Stock_plate3, A7")


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
        

        with st.expander("OT2 convert:"):
            lv1_metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label="Metadata").replace("\n", "\n    ")
            lv1_requirements = st.text_area(value='"robotType": "OT-2", "apiLevel": "2.17"', label="Requirements")
            labware_options = [
                            "corning_96_wellplate_360ul_flat",
                            "opentrons_96_tiprack_300ul",
                            "biorad_96_wellplate_200ul_pcr",
                            "nest_96_wellplate_2ml_deep",
                            "usascientific_12_reservoir_22ml",
                            "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap"
                        ]
            lv1_plate_posit = []
            lv1_plate_types = []
            
            for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
                col1, col2 = st.columns(2)
                with col1:
                    position = st.selectbox(options=range(1, 12), label=f"{plate} position:", index=i, key = f"lv1_pos_{i}")
                with col2:
                    labware_type = st.selectbox(f"{plate} labware type", options=labware_options, index=0, key=f"lv1_labware_type_{i}")
                lv1_plate_posit.append([plate, position])
                lv1_plate_types.append([plate, labware_type])
            
            for i, plate in enumerate(lv1_destination_names):
                col1, col2 = st.columns(2)
                with col1:
                    position = st.selectbox(options=range(1, 12), label=f"{plate} position:", index=i, key = f"lv1_dpos_{i}")
                with col2:
                    labware_type = st.selectbox(f"{plate} labware type", options=labware_options, index=0, key=f"lv1_dlabware_type_{i}")
                lv1_plate_posit.append([plate, position])
                lv1_plate_types.append([plate, labware_type])
            
            # for j in range(lv1_plate_len):
            #     lv1_plate_posit.append([f"destination_{j}", st.selectbox(options=range(1, 12), label=f"Destination_{j+1} rack position:", key = f'lv1_destination_{j}', index=i+j+1)])
            lv1_plate_posit.append(["tiprack", st.selectbox(options=range(1, 12), label="Tiprack position:", index=i+2)])
            converted_protocol = protocol_to_ot2_script(lv1_protocol, lv1_metadata, lv1_requirements, lv1_plate_posit)
            st.code(converted_protocol, language='python')


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
        lv2_protocol, lv2_outputs = generate_protocol(designs2, lv2_destination_names, lv2_sources, plate_type=lv2_plate_type)

        
        st.write("Generated Lv2 mapping:")
        st.write(lv2_protocol.reset_index(drop=True))
        with st.expander("Generated Lv2 output plate:"):
            st.write(lv2_outputs.reset_index(drop=True))
        

        st.write("updated sources:")
        st.write(lv2_sources.reset_index(drop=True))

        # with st.expander("OT2 convert:"):
        #     lv2_metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label="Metadata", key="lv2_meta").replace("\n", "\n    ")
        #     lv2_requirements = st.text_area(value='"robotType": "OT-2", "apiLevel": "2.17"', label="Requirements", key="lv2_reqs")
        #     lv2_plate_posit = []
        #     lv2_plate_posit.append(["destination", st.selectbox(options=range(1, 12), label="destination_rack position:", index=i+1, key = "lv2_dpos")])
        #     lv2_plate_posit.append(["tiprack", st.selectbox(options=range(1, 12), label="tibrack position:", index=i+2, key = "lv2_tpos")])
        #     converted_protocol = protocol_to_ot2_script(lv2_protocol, lv2_metadata, lv2_requirements, lv2_plate_posit)
        #     st.code(converted_protocol, language='python')

        with st.expander("OT2 convert:"):
            lv2_metadata = st.text_area(value="""'protocolName': 'Custom Protocol',\n'robotType': 'OT-2'""", label="Metadata", key = 'lv2_metadata').replace("\n", "\n    ")
            lv2_requirements = st.text_area(value='"robotType": "OT-2", "apiLevel": "2.17"', label="Requirements", key = 'lv2_requirements')
            labware_options = [
                            "corning_96_wellplate_360ul_flat",
                            "opentrons_96_tiprack_300ul",
                            "biorad_96_wellplate_200ul_pcr",
                            "nest_96_wellplate_2ml_deep",
                            "usascientific_12_reservoir_22ml",
                            "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap"
                        ]
            lv2_plate_posit = []
            lv2_plate_types = []
            
            for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
                col1, col2 = st.columns(2)
                with col1:
                    position = st.selectbox(options=range(1, 12), label=f"{plate} position:", index=i, key = f"lv2_pos_{i}")
                with col2:
                    labware_type = st.selectbox(f"{plate} labware type", options=labware_options, index=0, key=f"lv2_labware_type_{i}")
                lv2_plate_posit.append([plate, position])
                lv2_plate_types.append([plate, labware_type])
            
            for i, plate in enumerate(lv2_destination_names):
                col1, col2 = st.columns(2)
                with col1:
                    position = st.selectbox(options=range(1, 12), label=f"{plate} position:", index=i, key = f"lv2_dpos_{i}")
                with col2:
                    labware_type = st.selectbox(f"{plate} labware type", options=labware_options, index=0, key=f"lv2_dlabware_type_{i}")
                lv2_plate_posit.append([plate, position])
                lv2_plate_types.append([plate, labware_type])
            
            # for j in range(lv1_plate_len):
            #     lv1_plate_posit.append([f"destination_{j}", st.selectbox(options=range(1, 12), label=f"Destination_{j+1} rack position:", key = f'lv1_destination_{j}', index=i+j+1)])
            lv2_plate_posit.append(["tiprack", st.selectbox(options=range(1, 12), label="Tiprack position:", index=i+2, key = "lv2_tiprack")])
            converted_protocol = protocol_to_ot2_script(lv2_protocol, lv2_metadata, lv2_requirements, lv2_plate_posit)
            st.code(converted_protocol, language='python')
