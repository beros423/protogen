# functions
import streamlit as st
import pandas as pd
import os
from itertools import product


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