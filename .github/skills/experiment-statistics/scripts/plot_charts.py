#!/usr/bin/env python3
"""
실험 시간 통계 시각화 스크립트

Usage:
    python plot_charts.py --stats stats.json --output chart.png
"""

import json
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import Dict, Any


def plot_histogram(stats: Dict[str, Any], output_file: str):
    """
    시간 분포 히스토그램 생성
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # 1. 시간 분포 히스토그램
    distribution = stats.get('distribution', {})
    if distribution:
        ranges = list(distribution.keys())
        counts = list(distribution.values())
        
        ax1.bar(ranges, counts, color='steelblue', alpha=0.7, edgecolor='black')
        ax1.set_xlabel('Duration (hours)', fontsize=11)
        ax1.set_ylabel('Count', fontsize=11)
        ax1.set_title(f'Experiment Duration Distribution (n={stats["count"]})', 
                      fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 평균/중앙값 표시
        ax1.axvline(x=stats['mean'], color='red', linestyle='--', 
                    linewidth=2, label=f"Mean: {stats['mean']}h")
        ax1.axvline(x=stats['median'], color='green', linestyle='--', 
                    linewidth=2, label=f"Median: {stats['median']}h")
        ax1.legend()
    
    # 2. 타임라인 (최근 실험)
    recent = stats.get('recent_experiments', [])
    if recent:
        dates = [r['date'] for r in recent]
        durations = [r['value'] for r in recent]
        notes = [r['note'].replace('.md', '') for r in recent]
        
        # 날짜 파싱
        try:
            date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
            ax2.plot(date_objects, durations, marker='o', linestyle='-', 
                    color='steelblue', linewidth=2, markersize=8)
            ax2.set_xlabel('Date', fontsize=11)
            ax2.set_ylabel('Duration (hours)', fontsize=11)
            ax2.set_title('Recent Experiment Timeline', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            
            # 날짜 포맷
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 각 점에 노트명 표시
            for i, note in enumerate(notes):
                ax2.annotate(note[:15], (date_objects[i], durations[i]), 
                           textcoords="offset points", xytext=(0,10), 
                           ha='center', fontsize=8, alpha=0.7)
        except ValueError:
            # 날짜 파싱 실패 시 인덱스로 표시
            ax2.plot(range(len(durations)), durations, marker='o', linestyle='-')
            ax2.set_xlabel('Experiment Index', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"📊 그래프 저장: {output_file}")


def plot_box_plot(stats: Dict[str, Any], output_file: str):
    """
    Box plot으로 통계 요약 표시
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    
    durations = stats.get('durations', [])
    if durations:
        values = [d['value'] for d in durations]
        
        bp = ax.boxplot([values], vert=True, patch_artist=True, 
                        labels=['Duration (hours)'])
        
        # 색상 설정
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][0].set_alpha(0.7)
        
        ax.set_ylabel('Hours', fontsize=12)
        ax.set_title(f'Experiment Duration Statistics (n={stats["count"]})', 
                    fontsize=13, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # 통계 정보 텍스트
        textstr = f"Mean: {stats['mean']}h\nMedian: {stats['median']}h\n"
        textstr += f"Std Dev: {stats['std_dev']}h\nRange: {stats['min']}h - {stats['max']}h"
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.65, 0.95, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"📊 Box plot 저장: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Visualize experiment time statistics')
    parser.add_argument('--stats', required=True, help='Input JSON file with statistics')
    parser.add_argument('--output', required=True, help='Output image file')
    parser.add_argument('--type', choices=['histogram', 'boxplot'], 
                       default='histogram', help='Chart type')
    
    args = parser.parse_args()
    
    # 통계 로드
    with open(args.stats, 'r', encoding='utf-8') as f:
        stats = json.load(f)
    
    # 그래프 생성
    if args.type == 'histogram':
        plot_histogram(stats, args.output)
    elif args.type == 'boxplot':
        plot_box_plot(stats, args.output)


if __name__ == '__main__':
    main()
