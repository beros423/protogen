#!/usr/bin/env python3
"""
연구노트에서 Input/Output 파싱

Usage:
    python parse_notes.py --labnotes ./labnotes --output notes_data.json
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


def extract_sample_id(text: str) -> str:
    """
    샘플 ID 추출
    
    Pattern: DNA-20260102-001, Plasmid-20260102-002, Protein-20260103-001 등
    """
    pattern = r'([A-Z][A-Za-z]*-\d{8}-\d{3})'
    match = re.search(pattern, text)
    return match.group(1) if match else None


def extract_description(text: str, sample_id: str) -> str:
    """
    샘플 설명 추출 (괄호 안 정보)
    
    Example:
        "DNA-20260102-001 (PCR product, 45 μL)" -> "PCR product, 45 μL"
    """
    # 샘플 ID 제거
    desc = text.replace(sample_id, '').strip()
    
    # 앞의 '-' 제거
    desc = desc.lstrip('- ')
    
    # 괄호 안 내용 추출
    paren_match = re.search(r'\((.*?)\)', desc)
    if paren_match:
        return paren_match.group(1)
    
    return desc


def extract_unit_operation(text: str) -> Dict[str, str]:
    """
    섹션 제목에서 Unit Operation 정보 추출
    
    Examples:
        "### [Manual] PCR amplification" -> {'code': 'Manual', 'name': 'PCR amplification'}
        "### [UHW100 Thermocycling] Golden Gate" -> {'code': 'UHW100', 'name': 'Golden Gate'}
        "### \\[Manual\\] PCR amplification" -> {'code': 'Manual', 'name': 'PCR amplification'}
    """
    # 패턴: ### [UO_CODE] Experiment Name (이스케이프 고려)
    pattern = r'###\s*\\?\[([^\]]+)\\?\]\s*(.+?)(?:\n|$)'
    match = re.search(pattern, text)
    
    if match:
        uo_code = match.group(1).strip()
        uo_name = match.group(2).strip()
        return {
            'code': uo_code,
            'name': uo_name,
            'full': f"{uo_code}: {uo_name}"
        }
    
    return None


def parse_labnote(file_path: Path) -> Dict[str, Any]:
    """
    단일 연구노트 파싱
    
    Returns:
        {
            'file': '20260102_001.md',
            'date': '2026-01-02',
            'title': 'PCR Test',
            'unit_operation': {'code': 'Manual', 'name': 'PCR amplification'},
            'inputs': [{'id': 'DNA-20251220-005', 'text': '...', 'desc': '...'}],
            'outputs': [{'id': 'DNA-20260102-001', 'text': '...', 'desc': '...'}]
        }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ 파일 읽기 실패: {file_path} - {e}")
        return None
    
    # 메타데이터 추출
    date_match = re.search(r'Created_date:\s*(\d{4}-\d{2}-\d{2})', content)
    title_match = re.search(r'Title:\s*"?([^"\n]+)"?', content)
    
    # Unit Operation 추출
    unit_operation = extract_unit_operation(content)
    
    # Input 섹션 추출
    inputs = []
    input_match = re.search(r'####\s*Input\s*\n(.*?)(?=####|---|\n\n\n)', content, re.DOTALL)
    if input_match:
        for line in input_match.group(1).split('\n'):
            line = line.strip()
            if line.startswith('-'):
                sample_id = extract_sample_id(line)
                if sample_id:
                    desc = extract_description(line, sample_id)
                    inputs.append({
                        'id': sample_id,
                        'text': line,
                        'desc': desc
                    })
    
    # Output 섹션 추출
    outputs = []
    output_match = re.search(r'####\s*Output\s*\n(.*?)(?=####|---|\n\n\n)', content, re.DOTALL)
    if output_match:
        for line in output_match.group(1).split('\n'):
            line = line.strip()
            if line.startswith('-'):
                sample_id = extract_sample_id(line)
                if sample_id:
                    desc = extract_description(line, sample_id)
                    outputs.append({
                        'id': sample_id,
                        'text': line,
                        'desc': desc
                    })
    
    return {
        'file': file_path.name,
        'path': str(file_path),
        'date': date_match.group(1) if date_match else 'unknown',
        'title': title_match.group(1).strip() if title_match else file_path.stem,
        'unit_operation': unit_operation,
        'inputs': inputs,
        'outputs': outputs
    }


def parse_all_labnotes(labnotes_dir: Path) -> List[Dict[str, Any]]:
    """
    labnotes 폴더의 모든 .md 파일 파싱
    """
    results = []
    
    md_files = list(labnotes_dir.glob('*.md'))
    
    # 템플릿 파일 제외
    md_files = [f for f in md_files if 'template' not in f.name.lower()]
    
    print(f"📂 {len(md_files)}개의 노트 발견")
    
    for md_file in sorted(md_files):
        print(f"   파싱 중: {md_file.name}")
        data = parse_labnote(md_file)
        if data and (data['inputs'] or data['outputs']):
            results.append(data)
            uo_info = data.get('unit_operation')
            uo_str = uo_info['full'] if uo_info else 'Unknown'
            print(f"      ✅ UO: {uo_str}, Input: {len(data['inputs'])}, Output: {len(data['outputs'])}")
        else:
            print(f"      ⚠️ Input/Output 없음, 스킵")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Parse lab notes for Input/Output')
    parser.add_argument('--labnotes', required=True, help='Path to labnotes directory')
    parser.add_argument('--output', required=True, help='Output JSON file')
    
    args = parser.parse_args()
    
    labnotes_dir = Path(args.labnotes)
    
    if not labnotes_dir.exists():
        print(f"❌ 디렉토리 없음: {labnotes_dir}")
        return
    
    # 파싱 실행
    notes_data = parse_all_labnotes(labnotes_dir)
    
    # 결과 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(notes_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 파싱 완료: {len(notes_data)}개 노트")
    print(f"   저장: {args.output}")


if __name__ == '__main__':
    main()
