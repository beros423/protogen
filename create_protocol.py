#!/usr/bin/env python3
"""
Protocol Generator for Liquid Handling Robots
Converts assembly designs to executable protocols for Janus or OT-2.

Usage:
    python create_protocol.py config.json -o output_dir
"""

import json
import argparse
import pandas as pd
from pathlib import Path


def find_source_well(sources_df, name, required_volume):
    """
    Find source well with sufficient volume and update remaining volume.
    
    Args:
        sources_df: DataFrame with source information (modified in place)
        name: Name of the part to find
        required_volume: Volume required
        
    Returns:
        Tuple of (plate, well)
        
    Raises:
        ValueError: If not enough volume available
    """
    sources_row = sources_df[
        (sources_df['name'] == name) & 
        (sources_df['volume'] >= required_volume)
    ]
    
    if sources_row.empty:
        raise ValueError(f"Not enough volume available for '{name}'")
    
    row = sources_row.iloc[0]
    sources_df.loc[
        (sources_df['name'] == row['name']) & 
        (sources_df['plate'] == row['plate']) & 
        (sources_df['well'] == row['well']), 
        'volume'
    ] -= required_volume
    
    return row['plate'], row['well']


def generate_janus_protocol(sources_df, designs, destination_name, sources_original, plate_type=96):
    """
    Generate Janus liquid handler protocol.
    
    Args:
        sources_df: DataFrame with source information (will be modified)
        designs: List of design dictionaries
        destination_name: Name of destination plate
        sources_original: Original sources DataFrame for error checking
        plate_type: Plate type (96 or 384)
        
    Returns:
        Tuple of (protocol_df, output_df)
    """
    protocol_rows = pd.DataFrame(columns=[
        "Component", "Asp.Rack", "Asp.Posi", "Dsp.Rack", "Dsp.Posi", "Volume", "Note"
    ])
    output_rows = pd.DataFrame(columns=[
        "name", "plate", "well", "volume", "note"
    ])
    
    # Set row length based on plate type
    row_len = 12 if plate_type == 96 else 24
    dest_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]
    
    volume_error = False
    
    for index, design in enumerate(designs):
        if volume_error:
            raise ValueError("Volume error occurred during protocol generation")
        
        # Calculate destination well
        dest_row = int(index / row_len)
        dest_col = index + 1 - row_len * dest_row
        destination = f"{dest_list[dest_row]}{dest_col}"
        
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
            "name": f"{destination_name}_{index+1}",
            "plate": destination_name,
            "well": destination,
            "volume": 0,
            "note": ""
        }
        
        # Process each part in the design
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']
            
            try:
                plate, well = find_source_well(sources_df, name, vol)
            except ValueError as e:
                # Calculate total needed vs available
                total_need = sum(
                    part['volume'] 
                    for d in designs 
                    for part in d 
                    if part['name'] == name
                )
                total_have = sources_original.loc[
                    sources_original['name'] == name, 'volume'
                ].sum()
                
                error_msg = f"Not enough '{name}': have {total_have}µL, need {total_need}µL"
                raise ValueError(error_msg)
            
            protocol_row["Asp.Rack"] = plate
            protocol_row["Asp.Posi"] = well
            protocol_row["Note"] = name
            protocol_row["Volume"] = vol
            
            output_row['note'] += f"{name}/"
            output_row['volume'] += vol
            output_row[k] = name
            
            protocol_rows = pd.concat([protocol_rows, pd.DataFrame([protocol_row])], ignore_index=True)
        
        output_row['note'] = output_row['note'].rstrip('/')
        output_rows = pd.concat([output_rows, pd.DataFrame([output_row])], ignore_index=True)
    
    return protocol_rows, output_rows


def generate_ot2_protocol(sources_df, designs, plate_positions, metadata, requirements, sources_original):
    """
    Generate OT-2 Python protocol script.
    
    Args:
        sources_df: DataFrame with source information (will be modified)
        designs: List of design dictionaries
        plate_positions: List of (plate_name, position) tuples
        metadata: Metadata string for OT-2
        requirements: Requirements string for OT-2
        sources_original: Original sources DataFrame for error checking
        
    Returns:
        Tuple of (protocol_script string, output_df)
    """
    output_rows = pd.DataFrame(columns=["name", "plate", "well", "volume", "note"])
    
    # Generate script header
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
    
    # Load labware
    for plate, position in plate_positions[:-1]:
        script += f"{plate} = protocol.load_labware('corning_96_wellplate_360ul_flat', {position})\n    "
    
    script += f"""
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', {plate_positions[-1][1]})
    p300 = protocol.load_instrument('p300_single', 'left', tip_racks=[tiprack])
    """
    
    dest_list = ["A", "B", "C", "D", "E", "F", "G", "H"]
    volume_error = False
    
    for index, design in enumerate(designs):
        if volume_error:
            raise ValueError("Volume error occurred during protocol generation")
        
        # Calculate destination well
        dest_row = int(index / 12)
        destination = f"{dest_list[dest_row]}{index + 1 - 12*dest_row}"
        
        output_row = {
            'name': "",
            'plate': "dest_01",
            'well': destination,
            'volume': 0,
            'note': None
        }
        
        script += f"\n\n    # Assembly design {index + 1}"
        
        # Process each part in the design
        for k, item in enumerate(design):
            name = item['name']
            vol = item['volume']
            output_row['name'] += name + "/"
            output_row['volume'] += vol
            output_row[k] = name
            
            try:
                plate, well = find_source_well(sources_df, name, vol)
            except ValueError:
                total_need = sum(
                    part['volume'] 
                    for d in designs 
                    for part in d 
                    if part['name'] == name
                )
                total_have = sources_original.loc[
                    sources_original['name'] == name, 'volume'
                ].sum()
                
                error_msg = f"Not enough '{name}': have {total_have}µL, need {total_need}µL"
                raise ValueError(error_msg)
            
            script += f"""
    p300.pick_up_tip()
    p300.aspirate({vol}, {plate}['{well}'])  # {name}
    p300.dispense({vol}, destination['{destination}'])
    p300.drop_tip()
    """
        
        output_row['name'] = output_row['name'].rstrip('/')
        output_rows = pd.concat([output_rows, pd.DataFrame([output_row])], ignore_index=True)
    
    return script, output_rows


def main():
    parser = argparse.ArgumentParser(
        description='Generate liquid handling protocol from assembly designs'
    )
    parser.add_argument(
        'config_file',
        type=str,
        help='Input JSON file with protocol configuration'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='.',
        help='Output directory for generated files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config_file)
    if not config_path.exists():
        print(f"Error: Config file '{args.config_file}' not found")
        return 1
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Validate required fields
    required_fields = ['designs_file', 'sources_file', 'protocol_type']
    for field in required_fields:
        if field not in config:
            print(f"Error: Missing required field '{field}' in config JSON")
            return 1
    
    # Load designs
    designs_path = Path(config['designs_file'])
    if not designs_path.exists():
        print(f"Error: Designs file '{config['designs_file']}' not found")
        return 1
    
    with open(designs_path, 'r', encoding='utf-8') as f:
        designs_data = json.load(f)
        designs = designs_data['designs']
    
    print(f"✓ Loaded {len(designs)} designs")
    
    # Load sources
    sources_path = Path(config['sources_file'])
    if not sources_path.exists():
        print(f"Error: Sources file '{config['sources_file']}' not found")
        return 1
    
    sources_df = pd.read_csv(sources_path, encoding='utf-8')
    sources_original = sources_df.copy()
    print(f"✓ Loaded {len(sources_df)} source wells")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate protocol based on type
    protocol_type = config['protocol_type'].lower()
    
    try:
        if protocol_type == 'janus':
            destination_name = config.get('destination_name', 'dest_01')
            plate_type = config.get('plate_type', 96)
            
            print(f"Generating Janus protocol for {plate_type}-well plate...")
            protocol_df, output_df = generate_janus_protocol(
                sources_df, designs, destination_name, sources_original, plate_type
            )
            
            # Save protocol
            protocol_path = output_dir / 'protocol.csv'
            protocol_df.to_csv(protocol_path, index=False, encoding='utf-8')
            print(f"✓ Protocol saved to {protocol_path}")
            
        elif protocol_type == 'ot2':
            metadata = config.get('metadata', "'protocolName': 'Custom Protocol', 'robotType': 'OT-2'")
            requirements = config.get('requirements', "'robotType': 'OT-2', 'apiLevel': '2.17'")
            plate_positions = [
                (p['plate'], p['position']) 
                for p in config.get('plate_positions', [])
            ]
            
            print("Generating OT-2 protocol...")
            protocol_script, output_df = generate_ot2_protocol(
                sources_df, designs, plate_positions, metadata, requirements, sources_original
            )
            
            # Save protocol
            protocol_path = output_dir / 'protocol.py'
            with open(protocol_path, 'w', encoding='utf-8') as f:
                f.write(protocol_script)
            print(f"✓ Protocol saved to {protocol_path}")
            
        else:
            print(f"Error: Unsupported protocol_type '{protocol_type}'. Use 'janus' or 'ot2'")
            return 1
        
        # Save output mapping
        output_path = output_dir / 'output_wells.csv'
        output_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✓ Output mapping saved to {output_path}")
        
        # Save updated sources
        sources_updated_path = output_dir / 'sources_updated.csv'
        sources_df.to_csv(sources_updated_path, index=False, encoding='utf-8')
        print(f"✓ Updated sources saved to {sources_updated_path}")
        
        print(f"\n✓ Protocol generation complete!")
        print(f"  Total assemblies: {len(designs)}")
        print(f"  Output wells: {len(output_df)}")
        
    except ValueError as e:
        print(f"\nError: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
