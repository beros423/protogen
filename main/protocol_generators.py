"""
Protocol generation functions for assembly designs
"""

import pandas as pd
import math


def generate_protocol(designs, destination_name, sources, plate_type=96, naming="TU"):
    """Generate protocol for assembly
    
    Args:
        designs: List of design dictionaries
        destination_name: List of destination plate names
        sources: DataFrame with source information
        plate_type: Plate type (6, 12, 24, 48, 96, 384)
        naming: Naming convention for outputs
        
    Returns:
        Tuple of (protocol_rows DataFrame, output_rows DataFrame)
    """
    protocol_rows = pd.DataFrame(columns=["Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"])
    output_rows = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    dest_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]
    dest_row_list = {"6":3, "12":4, "24":6, "48":8, "96":12, "384":24}  
    dest_row_num = dest_row_list.get(str(plate_type))
    volume_error = False
    group_counters = {}
    
    for index, design in enumerate(designs):
        if volume_error:
            protocol_rows, output_rows = None, None
            break
        plate_num = int(index/plate_type)
        dest_name = destination_name[plate_num]
        plate_index = index - plate_num*plate_type + 1
        dest_row = math.ceil(plate_index/dest_row_num) - 1
        destination = f"{dest_list[dest_row]}{plate_index - dest_row_num * (dest_row)}"
        
        group_name = design[0]['note']
        if group_name not in group_counters:
            group_counters[group_name] = 1
        else:
            group_counters[group_name] += 1

        protocol_row = {
            "Component": f"{naming + '_' if naming is not None else ''}{group_name}_{group_counters[group_name]}",
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
        
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']

            try:
                from .utils import find_source_well
                plate, well = find_source_well(sources, name, vol)
            except ValueError:
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


def protocol_to_ot2_script(protocol_rows, metadata, requirements, plate_posit):
    """Convert protocol to OT2 Python script
    
    Args:
        protocol_rows: DataFrame with protocol information
        metadata: Metadata string for OT2
        requirements: Requirements string for OT2
        plate_posit: List of (plate_name, position) tuples
        
    Returns:
        String containing OT2 Python script
    """
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


def create_ot2_labware_settings(sheet_names, destination_names, key_prefix):
    """Create OT2 labware position and type settings
    
    Args:
        sheet_names: List of source sheet names
        destination_names: List of destination plate names
        key_prefix: Prefix for UI element keys
        
    Returns:
        Tuple of (plate_posit list, plate_types list)
    """
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
    
    # This function needs to be implemented with UI callbacks in Dash
    # For now, return default configuration
    for i, plate in enumerate([s.replace(" ", "_") for s in sheet_names]):
        plate_posit.append([plate, i+1])
        plate_types.append([plate, labware_options[0]])
    
    for i, plate in enumerate(destination_names):
        plate_posit.append([plate, len(sheet_names)+i+1])
        plate_types.append([plate, labware_options[0]])
    
    plate_posit.append(["tiprack", len(sheet_names)+len(destination_names)+1])
    
    return plate_posit, plate_types
