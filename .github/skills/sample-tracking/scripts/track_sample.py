#!/usr/bin/env python3
"""
샘플 추적 분석 스크립트

Usage:
    python track_sample.py --data data.json --sample-id DNA-20250115-001 --output result.json
"""

import json
import argparse
from typing import Dict, List, Any, Set
from datetime import datetime


class SampleTracker:
    def __init__(self, notes_data: List[Dict[str, Any]]):
        """
        Args:
            notes_data: 노트 데이터 리스트
                [
                    {
                        "file": "20250115_001.md",
                        "date": "2025-01-15",
                        "outputs": ["DNA-20250115-001: 50 μL"],
                        "inputs": ["DNA-20250110-005", "DNA-20250110-006"]
                    },
                    ...
                ]
        """
        self.notes = notes_data
        self.sample_index = self._build_sample_index()
    
    def _build_sample_index(self) -> Dict[str, Dict[str, Any]]:
        """
        샘플 ID를 키로 하는 인덱스 생성
        
        Returns:
            {
                "DNA-20250115-001": {
                    "created_in": "20250115_001.md",
                    "created_date": "2025-01-15",
                    "used_in": ["20250116_002.md", "20250118_001.md"],
                    "volume": "50 μL",
                    ...
                }
            }
        """
        index = {}
        
        for note in self.notes:
            note_file = note.get('file', '')
            note_date = note.get('date', '')
            
            # Output에서 생성된 샘플
            for output in note.get('outputs', []):
                sample_id = self._extract_sample_id(output)
                if sample_id:
                    if sample_id not in index:
                        index[sample_id] = {
                            'created_in': note_file,
                            'created_date': note_date,
                            'used_in': [],
                            'volume': self._extract_volume(output),
                            'description': output
                        }
            
            # Input에서 사용된 샘플
            for input_item in note.get('inputs', []):
                sample_id = self._extract_sample_id(input_item)
                if sample_id:
                    if sample_id not in index:
                        index[sample_id] = {
                            'created_in': 'unknown',
                            'created_date': 'unknown',
                            'used_in': [],
                            'volume': None,
                            'description': input_item
                        }
                    
                    # 사용 이력 추가
                    usage = {
                        'note': note_file,
                        'date': note_date,
                        'usage_amount': self._extract_volume(input_item)
                    }
                    index[sample_id]['used_in'].append(usage)
        
        return index
    
    def _extract_sample_id(self, text: str) -> str:
        """
        텍스트에서 샘플 ID 추출
        
        Examples:
            "DNA-20250115-001: 50 μL" -> "DNA-20250115-001"
            "Plasmid-20250110-003" -> "Plasmid-20250110-003"
        """
        import re
        # 패턴: 대문자-날짜-번호 (예: DNA-20250115-001, Plasmid-20250110-003)
        pattern = r'([A-Z][A-Za-z]*-\d{8}-\d{3})'
        match = re.search(pattern, text)
        return match.group(1) if match else None
    
    def _extract_volume(self, text: str) -> str:
        """
        텍스트에서 용량 정보 추출
        
        Examples:
            "DNA-20250115-001: 50 μL" -> "50 μL"
            "Sample (10 mL)" -> "10 mL"
        """
        import re
        # 패턴: 숫자 + 단위 (μL, mL, L, ng, μg, mg 등)
        pattern = r'(\d+(?:\.\d+)?)\s*(μL|mL|L|μl|ml|ng|μg|mg|g)'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def get_source_tree(self, sample_id: str, visited: Set[str] = None) -> Dict[str, Any]:
        """
        샘플의 출처 트리 생성 (재귀)
        
        Returns:
            {
                "sample_id": "DNA-20250115-001",
                "created_date": "2025-01-15",
                "created_in": "20250115_001.md",
                "parents": [
                    {"sample_id": "DNA-20250110-005", ...},
                    {"sample_id": "DNA-20250110-006", ...}
                ]
            }
        """
        if visited is None:
            visited = set()
        
        if sample_id in visited:
            return {"sample_id": sample_id, "circular_reference": True}
        
        visited.add(sample_id)
        
        info = self.sample_index.get(sample_id, {})
        created_note = info.get('created_in', 'unknown')
        
        tree = {
            "sample_id": sample_id,
            "created_date": info.get('created_date', 'unknown'),
            "created_in": created_note,
            "volume": info.get('volume'),
            "parents": []
        }
        
        # 부모 샘플 찾기 (해당 노트의 Input)
        for note in self.notes:
            if note.get('file') == created_note:
                for input_item in note.get('inputs', []):
                    parent_id = self._extract_sample_id(input_item)
                    if parent_id:
                        parent_tree = self.get_source_tree(parent_id, visited.copy())
                        tree['parents'].append(parent_tree)
        
        return tree
    
    def get_usage_history(self, sample_id: str) -> List[Dict[str, Any]]:
        """
        샘플 사용 이력 조회 (시간순 정렬)
        
        Returns:
            [
                {
                    "date": "2025-01-16",
                    "note": "20250116_002.md",
                    "usage_amount": "2 μL"
                },
                ...
            ]
        """
        info = self.sample_index.get(sample_id, {})
        usage = info.get('used_in', [])
        
        # 날짜순 정렬
        sorted_usage = sorted(usage, key=lambda x: x.get('date', ''))
        return sorted_usage
    
    def get_derived_samples(self, sample_id: str) -> List[Dict[str, Any]]:
        """
        파생 샘플 리스트 (이 샘플을 Input으로 사용한 실험의 Output)
        
        Returns:
            [
                {
                    "sample_id": "Plasmid-20250118-005",
                    "created_date": "2025-01-18",
                    "created_in": "20250118_001.md"
                },
                ...
            ]
        """
        derived = []
        
        # 이 샘플을 사용한 노트 찾기
        info = self.sample_index.get(sample_id, {})
        used_notes = [u['note'] for u in info.get('used_in', [])]
        
        # 해당 노트들의 Output 수집
        for note in self.notes:
            if note.get('file') in used_notes:
                for output in note.get('outputs', []):
                    derived_id = self._extract_sample_id(output)
                    if derived_id and derived_id != sample_id:
                        derived.append({
                            'sample_id': derived_id,
                            'created_date': note.get('date', 'unknown'),
                            'created_in': note.get('file', 'unknown'),
                            'description': output
                        })
        
        return derived
    
    def calculate_volume_tracking(self, sample_id: str) -> Dict[str, Any]:
        """
        용량 추적 (제작량 - 사용량)
        
        Returns:
            {
                "initial_volume": "50 μL",
                "total_used": "8 μL",
                "remaining": "42 μL",
                "usage_breakdown": [...]
            }
        """
        info = self.sample_index.get(sample_id, {})
        initial = info.get('volume', 'unknown')
        
        usage = self.get_usage_history(sample_id)
        
        # 용량 파싱 (간단한 예시, 실제로는 더 정교한 파싱 필요)
        def parse_volume(vol_str):
            if not vol_str:
                return None
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', vol_str)
            return float(match.group(1)) if match else None
        
        initial_val = parse_volume(initial)
        used_vals = [parse_volume(u.get('usage_amount')) for u in usage]
        used_vals = [v for v in used_vals if v is not None]
        
        total_used = sum(used_vals) if used_vals else 0
        remaining = initial_val - total_used if initial_val else None
        
        return {
            'initial_volume': initial,
            'initial_value': initial_val,
            'total_used': f"{total_used} μL" if used_vals else "unknown",
            'total_used_value': total_used,
            'remaining': f"{remaining} μL" if remaining is not None else "unknown",
            'remaining_value': remaining,
            'usage_breakdown': usage
        }


def main():
    parser = argparse.ArgumentParser(description='Track sample ID through lab notes')
    parser.add_argument('--data', required=True, help='Input JSON file with notes data')
    parser.add_argument('--sample-id', required=True, help='Sample ID to track')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--mode', choices=['source', 'usage', 'derived', 'volume', 'all'],
                       default='all', help='Tracking mode')
    
    args = parser.parse_args()
    
    # 데이터 로드
    with open(args.data, 'r', encoding='utf-8') as f:
        notes_data = json.load(f)
    
    # 추적 실행
    tracker = SampleTracker(notes_data)
    
    result = {
        'sample_id': args.sample_id,
        'timestamp': datetime.now().isoformat()
    }
    
    if args.mode in ['source', 'all']:
        result['source_tree'] = tracker.get_source_tree(args.sample_id)
    
    if args.mode in ['usage', 'all']:
        result['usage_history'] = tracker.get_usage_history(args.sample_id)
    
    if args.mode in ['derived', 'all']:
        result['derived_samples'] = tracker.get_derived_samples(args.sample_id)
    
    if args.mode in ['volume', 'all']:
        result['volume_tracking'] = tracker.calculate_volume_tracking(args.sample_id)
    
    # 결과 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 추적 완료: {args.sample_id}")
    print(f"   결과 저장: {args.output}")


if __name__ == '__main__':
    main()
