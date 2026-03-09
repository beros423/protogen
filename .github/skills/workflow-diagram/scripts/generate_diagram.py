#!/usr/bin/env python3
"""
Mermaid workflow diagram 생성

Usage:
    python generate_diagram.py --data notes_data.json --output workflow.mmd --style flowchart
"""

import json
import argparse
from typing import List, Dict, Any, Set
from collections import defaultdict


def sanitize_id(sample_id: str) -> str:
    """
    Mermaid 노드 ID로 사용 가능하도록 변환
    
    Example:
        "DNA-20260102-001" -> "DNA_20260102_001"
    """
    return sample_id.replace('-', '_')


def generate_mermaid_flowchart(notes_data: List[Dict[str, Any]], direction: str = 'LR') -> str:
    """
    Flowchart 스타일 다이어그램 생성 (Unit Operation 중심)
    
    구조: Input Sample → [Unit Operation] → Output Sample
    
    Args:
        direction: 'LR' (좌→우), 'TD' (위→아래), 'RL', 'BT'
    """
    mermaid_lines = [f"flowchart {direction}"]
    
    # 노드 수집
    all_samples = {}
    all_uo_nodes = {}
    edges = []
    uo_counter = 0
    
    for note in notes_data:
        note_file = note['file']
        note_date = note['date']
        note_title = note.get('title', note_file)
        
        # Unit Operation 정보
        uo_info = note.get('unit_operation')
        if uo_info:
            uo_code = uo_info['code']
            uo_name = uo_info['name']
        else:
            uo_code = 'Unknown'
            uo_name = note_title
        
        # UO 노드 생성
        uo_counter += 1
        uo_node_id = f"UO_{uo_counter}"
        
        # UO 레이블 (코드 + 이름 + 날짜)
        uo_label_parts = [uo_code, uo_name[:30] + '...' if len(uo_name) > 30 else uo_name]
        uo_label_parts.append(f"📅 {note_date}")
        
        all_uo_nodes[uo_node_id] = {
            'id': uo_node_id,
            'label': '<br/>'.join(uo_label_parts),
            'code': uo_code
        }
        
        # Input 샘플들 → UO 연결
        for input_item in note['inputs']:
            input_id = input_item['id']
            input_node_id = sanitize_id(input_id)
            
            # Input 샘플 노드 추가
            if input_id not in all_samples:
                input_desc = input_item.get('desc', '')
                if len(input_desc) > 40:
                    input_desc = input_desc[:37] + '...'
                
                all_samples[input_id] = {
                    'id': input_node_id,
                    'label': f"{input_id}<br/>{input_desc}" if input_desc else input_id,
                    'type': input_id.split('-')[0]
                }
            
            # Input → UO 엣지
            edges.append({
                'from': input_node_id,
                'to': uo_node_id,
                'label': ''
            })
        
        # UO → Output 샘플들 연결
        for output in note['outputs']:
            sample_id = output['id']
            desc = output.get('desc', '')
            
            node_id = sanitize_id(sample_id)
            
            # Output 샘플 노드 추가
            if len(desc) > 40:
                desc = desc[:37] + '...'
            
            all_samples[sample_id] = {
                'id': node_id,
                'label': f"{sample_id}<br/>{desc}" if desc else sample_id,
                'type': sample_id.split('-')[0]
            }
            
            # UO → Output 엣지
            edges.append({
                'from': uo_node_id,
                'to': node_id,
                'label': ''
            })
    
    # 노드 정의
    mermaid_lines.append('')
    mermaid_lines.append('    %% Input/Output Samples')
    
    for sample_id, sample in sorted(all_samples.items()):
        node_id = sample['id']
        label = sample['label']
        sample_type = sample['type']
        
        # 타입별 스타일 지정 (둥근 사각형)
        if sample_type == 'DNA':
            mermaid_lines.append(f'    {node_id}(["{label}"]):::dna')
        elif sample_type == 'Plasmid':
            mermaid_lines.append(f'    {node_id}(["{label}"]):::plasmid')
        elif sample_type == 'Protein':
            mermaid_lines.append(f'    {node_id}(["{label}"]):::protein')
        else:
            mermaid_lines.append(f'    {node_id}(["{label}"])')
    
    # UO 노드 정의
    mermaid_lines.append('')
    mermaid_lines.append('    %% Unit Operations')
    
    for uo_node_id, uo_node in all_uo_nodes.items():
        label = uo_node['label']
        code = uo_node['code']
        
        # UO는 육각형으로 표시
        if 'UHW' in code or 'UH' in code:
            # 자동화/반자동 UO는 다른 스타일
            mermaid_lines.append(f'    {uo_node_id}{{{{{label}}}}}:::uo_auto')
        else:
            # Manual은 일반 스타일
            mermaid_lines.append(f'    {uo_node_id}{{{{{label}}}}}:::uo_manual')
    
    # 엣지 정의
    mermaid_lines.append('')
    mermaid_lines.append('    %% Workflow Connections')
    for edge in edges:
        if edge['label']:
            mermaid_lines.append(f'    {edge["from"]} -->|{edge["label"]}| {edge["to"]}')
        else:
            mermaid_lines.append(f'    {edge["from"]} --> {edge["to"]}')
    
    # 스타일 정의
    mermaid_lines.append('')
    mermaid_lines.append('    %% Styles')
    mermaid_lines.append('    classDef dna fill:#e1f5ff,stroke:#01579b,stroke-width:2px')
    mermaid_lines.append('    classDef plasmid fill:#fff3e0,stroke:#e65100,stroke-width:2px')
    mermaid_lines.append('    classDef protein fill:#f3e5f5,stroke:#4a148c,stroke-width:2px')
    mermaid_lines.append('    classDef uo_manual fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px')
    mermaid_lines.append('    classDef uo_auto fill:#b2dfdb,stroke:#00695c,stroke-width:3px')
    
    return '\n'.join(mermaid_lines)


def generate_mermaid_timeline(notes_data: List[Dict[str, Any]]) -> str:
    """
    Timeline 스타일 다이어그램 생성 (날짜별 서브그래프)
    """
    mermaid_lines = ["flowchart TD"]
    
    # 날짜별 그룹화
    by_date = defaultdict(list)
    for note in notes_data:
        date = note['date']
        if date != 'unknown':
            by_date[date].append(note)
    
    # 날짜순 정렬
    sorted_dates = sorted(by_date.keys())
    
    all_edges = []
    
    # 서브그래프로 날짜별 노드 생성
    for date in sorted_dates:
        mermaid_lines.append(f'    subgraph "{date}"')
        
        for note in by_date[date]:
            # Output만 표시
            for output in note['outputs']:
                sample_id = output['id']
                node_id = sanitize_id(sample_id)
                desc = output.get('desc', '')
                
                label = f"{sample_id}<br/>{desc}" if desc else sample_id
                mermaid_lines.append(f'        {node_id}["{label}"]')
            
            # 엣지 수집
            for output in note['outputs']:
                output_id = sanitize_id(output['id'])
                for input_item in note['inputs']:
                    input_id = sanitize_id(input_item['id'])
                    all_edges.append((input_id, output_id))
        
        mermaid_lines.append('    end')
        mermaid_lines.append('')
    
    # 엣지 연결
    mermaid_lines.append('    %% Connections')
    for from_id, to_id in all_edges:
        mermaid_lines.append(f'    {from_id} --> {to_id}')
    
    return '\n'.join(mermaid_lines)


def generate_sample_trace(notes_data: List[Dict[str, Any]], sample_id: str, 
                         direction: str = 'TD') -> str:
    """
    특정 샘플을 중심으로 한 추적 다이어그램
    
    상위 샘플 (부모) → 대상 샘플 → 하위 샘플 (파생)
    """
    mermaid_lines = [f"flowchart {direction}"]
    
    target_node_id = sanitize_id(sample_id)
    nodes = set()
    edges = []
    
    # 대상 샘플 찾기
    target_note = None
    for note in notes_data:
        for output in note['outputs']:
            if output['id'] == sample_id:
                target_note = note
                break
        if target_note:
            break
    
    if not target_note:
        return f"flowchart {direction}\n    {target_node_id}[{sample_id}<br/>❌ Not Found]"
    
    # 대상 샘플 노드 추가
    target_output = next((o for o in target_note['outputs'] if o['id'] == sample_id), None)
    target_desc = target_output.get('desc', '') if target_output else ''
    nodes.add((sample_id, target_desc, 'target'))
    
    # 부모 샘플들 (Input)
    for input_item in target_note['inputs']:
        input_id = input_item['id']
        input_desc = input_item.get('desc', '')
        nodes.add((input_id, input_desc, 'parent'))
        edges.append((sanitize_id(input_id), target_node_id, target_note['date']))
    
    # 파생 샘플들 (이 샘플을 Input으로 사용하는 것들)
    for note in notes_data:
        for input_item in note['inputs']:
            if input_item['id'] == sample_id:
                # 이 노트의 Output들이 파생 샘플
                for output in note['outputs']:
                    derived_id = output['id']
                    derived_desc = output.get('desc', '')
                    nodes.add((derived_id, derived_desc, 'derived'))
                    edges.append((target_node_id, sanitize_id(derived_id), note['date']))
    
    # 노드 정의
    mermaid_lines.append('')
    for node_id, desc, node_type in sorted(nodes, key=lambda x: x[2]):
        node_mmd_id = sanitize_id(node_id)
        label = f"{node_id}<br/>{desc}" if desc else node_id
        
        if node_type == 'target':
            mermaid_lines.append(f'    {node_mmd_id}["{label}"]:::target')
        elif node_type == 'parent':
            mermaid_lines.append(f'    {node_mmd_id}["{label}"]:::parent')
        elif node_type == 'derived':
            mermaid_lines.append(f'    {node_mmd_id}["{label}"]:::derived')
    
    # 엣지 정의
    mermaid_lines.append('')
    for from_id, to_id, date in edges:
        mermaid_lines.append(f'    {from_id} -->|{date}| {to_id}')
    
    # 스타일
    mermaid_lines.append('')
    mermaid_lines.append('    classDef target fill:#ffeb3b,stroke:#f57f17,stroke-width:3px')
    mermaid_lines.append('    classDef parent fill:#e3f2fd,stroke:#1565c0,stroke-width:2px')
    mermaid_lines.append('    classDef derived fill:#f1f8e9,stroke:#558b2f,stroke-width:2px')
    
    return '\n'.join(mermaid_lines)


def main():
    parser = argparse.ArgumentParser(description='Generate Mermaid workflow diagram')
    parser.add_argument('--data', required=True, help='Input JSON file with notes data')
    parser.add_argument('--output', required=True, help='Output Mermaid file (.mmd or .md)')
    parser.add_argument('--style', choices=['flowchart', 'timeline', 'trace'], 
                       default='flowchart', help='Diagram style')
    parser.add_argument('--direction', choices=['LR', 'TD', 'RL', 'BT'], 
                       default='LR', help='Flowchart direction')
    parser.add_argument('--sample-id', help='Sample ID for trace mode')
    parser.add_argument('--markdown', action='store_true', 
                       help='Wrap in markdown code block')
    
    args = parser.parse_args()
    
    # 데이터 로드
    with open(args.data, 'r', encoding='utf-8') as f:
        notes_data = json.load(f)
    
    # 다이어그램 생성
    if args.style == 'flowchart':
        mermaid_code = generate_mermaid_flowchart(notes_data, args.direction)
    elif args.style == 'timeline':
        mermaid_code = generate_mermaid_timeline(notes_data)
    elif args.style == 'trace':
        if not args.sample_id:
            print("❌ --sample-id 필수 (trace 모드)")
            return
        mermaid_code = generate_sample_trace(notes_data, args.sample_id, args.direction)
    
    # 마크다운으로 감싸기
    if args.markdown or args.output.endswith('.md'):
        output_content = f"# Workflow Diagram\n\n```mermaid\n{mermaid_code}\n```\n"
    else:
        output_content = mermaid_code
    
    # 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"✅ 다이어그램 생성: {args.output}")
    print(f"   스타일: {args.style}")
    print(f"   노트: {len(notes_data)}개")


if __name__ == '__main__':
    main()
