#!/usr/bin/env python3
"""
실험 시간 통계 분석 스크립트

Usage:
    python analyze_stats.py --data data.json --output stats.json
"""

import json
import argparse
from datetime import datetime
from statistics import mean, median, stdev
from typing import List, Dict, Any


def parse_duration(duration_str: str) -> float:
    """
    Duration 문자열을 시간(hours)으로 변환
    
    Examples:
        "2.5 hours" -> 2.5
        "1.5h" -> 1.5
        "90 minutes" -> 1.5
        "2h 30m" -> 2.5
    """
    duration_str = duration_str.lower().strip()
    
    # "2.5 hours" 형태
    if 'hour' in duration_str:
        return float(duration_str.split()[0])
    
    # "1.5h" 형태
    if duration_str.endswith('h'):
        return float(duration_str.rstrip('h'))
    
    # "90 minutes" 형태
    if 'minute' in duration_str or duration_str.endswith('m'):
        minutes = float(duration_str.split()[0].rstrip('m'))
        return minutes / 60
    
    # "2h 30m" 형태
    if 'h' in duration_str and 'm' in duration_str:
        parts = duration_str.replace('h', '').replace('m', '').split()
        hours = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        return hours + (minutes / 60)
    
    # 숫자만 있으면 시간으로 간주
    try:
        return float(duration_str)
    except ValueError:
        return None


def calculate_time_from_timestamps(start: str, end: str) -> float:
    """
    Time Started/Ended에서 Duration 계산
    
    Examples:
        "10:00", "13:30" -> 3.5
    """
    try:
        fmt = "%H:%M"
        start_time = datetime.strptime(start, fmt)
        end_time = datetime.strptime(end, fmt)
        delta = end_time - start_time
        return delta.total_seconds() / 3600
    except:
        return None


def analyze_experiment_times(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    실험 시간 데이터 분석
    
    Args:
        data: 노트 데이터 리스트
            [
                {
                    "note_file": "20250120_003_pcr.md",
                    "date": "2025-01-20",
                    "duration": "2.0 hours",
                    "time_started": "10:00",
                    "time_ended": "12:00",
                    "method_time": "1.5 hours"
                },
                ...
            ]
    
    Returns:
        통계 결과
    """
    durations = []
    method_times = []
    dates = []
    
    for entry in data:
        # Duration 추출
        duration = None
        if 'duration' in entry and entry['duration']:
            duration = parse_duration(entry['duration'])
        elif 'time_started' in entry and 'time_ended' in entry:
            duration = calculate_time_from_timestamps(
                entry['time_started'], 
                entry['time_ended']
            )
        
        if duration:
            durations.append({
                'value': duration,
                'note': entry.get('note_file', 'unknown'),
                'date': entry.get('date', 'unknown')
            })
            dates.append(entry.get('date', 'unknown'))
        
        # Method 시간 추출
        if 'method_time' in entry and entry['method_time']:
            method_time = parse_duration(entry['method_time'])
            if method_time:
                method_times.append(method_time)
    
    if not durations:
        return {
            'error': 'No valid duration data found',
            'count': 0
        }
    
    duration_values = [d['value'] for d in durations]
    
    # 통계 계산
    stats = {
        'count': len(durations),
        'mean': round(mean(duration_values), 2),
        'median': round(median(duration_values), 2),
        'min': round(min(duration_values), 2),
        'max': round(max(duration_values), 2),
        'std_dev': round(stdev(duration_values), 2) if len(duration_values) > 1 else 0,
        'total_hours': round(sum(duration_values), 2),
        'durations': durations,
        'dates': sorted(set(dates), reverse=True)[:10]  # 최근 10개 날짜
    }
    
    # Method 시간 통계
    if method_times:
        stats['method_time'] = {
            'mean': round(mean(method_times), 2),
            'median': round(median(method_times), 2),
            'min': round(min(method_times), 2),
            'max': round(max(method_times), 2)
        }
    
    # 시간 분포 계산
    stats['distribution'] = calculate_distribution(duration_values)
    
    # 최근 실험 리스트
    recent = sorted(durations, key=lambda x: x['date'], reverse=True)[:5]
    stats['recent_experiments'] = recent
    
    return stats


def calculate_distribution(values: List[float]) -> Dict[str, int]:
    """
    시간 분포 계산
    
    Returns:
        {
            "1.0-2.0h": 5,
            "2.0-3.0h": 8,
            ...
        }
    """
    distribution = {}
    
    # 1시간 단위로 분포 계산
    min_val = int(min(values))
    max_val = int(max(values)) + 1
    
    for i in range(min_val, max_val):
        range_key = f"{i}.0-{i+1}.0h"
        count = sum(1 for v in values if i <= v < i+1)
        if count > 0:
            distribution[range_key] = count
    
    return distribution


def main():
    parser = argparse.ArgumentParser(description='Analyze experiment time statistics')
    parser.add_argument('--data', required=True, help='Input JSON file with experiment data')
    parser.add_argument('--output', required=True, help='Output JSON file for statistics')
    
    args = parser.parse_args()
    
    # 데이터 로드
    with open(args.data, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 통계 분석
    stats = analyze_experiment_times(data)
    
    # 결과 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # 콘솔 출력
    print(f"✅ 분석 완료: {stats['count']}개 실험")
    print(f"   평균: {stats['mean']}h, 중앙값: {stats['median']}h")
    print(f"   범위: {stats['min']}h ~ {stats['max']}h")
    print(f"   결과 저장: {args.output}")


if __name__ == '__main__':
    main()
