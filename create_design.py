#!/usr/bin/env python3
"""
Universal Assembly Design Generator
Creates all possible assembly combinations from input specification.

Usage:
    python create_design.py input_design.json -o designs.json
"""

import json
import argparse
from itertools import product
from pathlib import Path


def generate_designs(config):
    """
    Generate all assembly design combinations from configuration.
    
    Args:
        config: Dict containing assemblies, part_types, volumes, common_parts, repeats
        
    Returns:
        List of design dictionaries
    """
    assemblies = config['assemblies']
    part_types = config['part_types']
    volumes = config['volumes']
    common_parts = config.get('common_parts', [])
    repeats = config.get('repeats', 1)
    
    designs = []
    
    for assembly in assemblies:
        # Get parts for each type in this assembly
        parts_by_type = []
        for part_type in part_types:
            parts = assembly.get(part_type, [''])
            if not parts:
                parts = ['']
            parts_by_type.append(parts)
        
        # Generate all combinations for this assembly
        assembly_combinations = product(*parts_by_type)
        
        for combo in assembly_combinations:
            # Skip if any part is empty string
            if all(part != '' for part in combo):
                design = []
                
                # Add parts with volumes
                for part_type, part_name in zip(part_types, combo):
                    design.append({
                        'name': part_name,
                        'volume': volumes.get(part_type, 1.0)
                    })
                
                # Add common parts
                for common in common_parts:
                    design.append({
                        'name': common['name'],
                        'volume': common['volume']
                    })
                
                # Add design multiple times if repeats > 1
                for _ in range(repeats):
                    designs.append(design)
    
    return designs


def main():
    parser = argparse.ArgumentParser(
        description='Generate universal assembly designs from JSON configuration'
    )
    parser.add_argument(
        'input_file',
        type=str,
        help='Input JSON file with assembly configuration'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='designs.json',
        help='Output JSON file for generated designs (default: designs.json)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty print JSON output'
    )
    
    args = parser.parse_args()
    
    # Load input configuration
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' not found")
        return 1
    
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Validate required fields
    required_fields = ['assemblies', 'part_types', 'volumes']
    for field in required_fields:
        if field not in config:
            print(f"Error: Missing required field '{field}' in input JSON")
            return 1
    
    # Generate designs
    print(f"Generating designs from {len(config['assemblies'])} assemblies...")
    designs = generate_designs(config)
    print(f"✓ Generated {len(designs)} assembly designs")
    
    # Calculate total volume per assembly
    if designs:
        total_vol = sum(part['volume'] for part in designs[0])
        print(f"✓ Total volume per assembly: {total_vol} µL")
    
    # Save output
    output_path = Path(args.output)
    output_data = {
        'designs': designs,
        'metadata': {
            'total_designs': len(designs),
            'part_types': config['part_types'],
            'volumes': config['volumes'],
            'repeats': config.get('repeats', 1)
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        if args.pretty:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(output_data, f, ensure_ascii=False)
    
    print(f"✓ Designs saved to {args.output}")
    
    return 0


if __name__ == '__main__':
    exit(main())
