---
name: experiment-statistics
description: Analyze experiment duration statistics from K-BioFoundry lab notes (./labnotes) using local file search. Provides mean, median, range, and timeline for specific Unit Operations or Workflows. Use when user asks how long experiments take, average time, or time statistics.
---

# K-BioFoundry Experiment Time Statistics

이 skill은 로컬 labnotes 폴더의 연구노트를 검색하여 특정 실험/프로토콜의 소요 시간 통계를 분석하고 예측합니다.

## 주요 기능

1. **평균/중앙값/범위 계산**: 특정 실험 유형의 시간 통계 분석
2. **최근 이력 추적**: 최근 수행된 실험들의 시간 데이터
3. **시간 분포 분석**: 시간대별 실험 건수 파악
4. **실험 계획 지원**: 권장 소요 시간 및 변수 고려사항 제안

## 사용 시점

- "Golden Gate 얼마나 걸려?"
- "PCR 평균 시간 알려줘"
- "Transformation 시간 통계"
- 특정 실험/프로토콜의 소요 시간 통계 요청

---

## 작업 절차

### 1. 실험 유형 식별

사용자가 요청한 Unit Operation, Workflow, 프로토콜 이름 확인

예시:
- **Unit Operations**: PCR, Golden Gate Assembly, Transformation, Sequencing, Cell culture, Protein purification
- **Workflows**: Cloning workflow, Strain construction, Protein expression pipeline

모호한 경우 사용자에게 확인:
```
PCR의 반응 시간만 알고 싶으신가요, 아니면 준비부터 정제까지 전체 시간인가요?
```

### 2. 로컬 노트 검색 수행

해당 실험 유형이 포함된 노트 검색 (./labnotes 폴더):
```
# semantic_search 사용
query: "Golden Gate Assembly method protocol duration time"
```

또는 grep_search 사용:
```
query: "Golden Gate Assembly|GoldenGate|golden gate"
isRegexp: true
includePattern: "labnotes/**/*.md"
```

Method 섹션에 해당 프로토콜이 있는 노트들만 필터링

### 3. 시간 데이터 추출

각 노트에서 시간 정보 수집:
- **메타데이터**: Time Started, Time Ended, Duration
- **Method 섹션**: 반응 시간, 배양 시간, 대기 시간 등
- **날짜**: Created_date, Date 필드

추출 대상 예시:
```
노트 1: Golden Gate Assembly
- Time Started: 10:00
- Time Ended: 13:30
- Duration: 3.5 hours
- Method 내 반응 시간: 37°C 2시간, 50°C 15분

노트 2: Golden Gate Assembly
- Duration: 4 hours
- Method 내 반응 시간: 37°C 3시간
```

### 4. 통계 분석

수집된 시간 데이터 분석:
- **평균 (Mean)**: 전체 평균 소요 시간
- **중앙값 (Median)**: 이상치 제거 시 유용
- **최소/최대**: 가장 짧은/긴 경우
- **표준편차**: 시간 변동성
- **샘플 수**: 몇 개의 노트에서 데이터 수집했는지

시간 단위 통일 (분 또는 시간)
이상치 확인 (예: 24시간 배양 vs 2시간 반응)

### 5. Python 스크립트로 통계 분석

#### 데이터 준비

검색/추출된 노트 데이터를 JSON 형식으로 정리:
```json
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
```

#### 스크립트 실행

**1단계: 통계 계산**
```bash
python .github/skills/experiment-statistics/scripts/analyze_stats.py \
  --data experiment_data.json \
  --output stats_result.json
```

출력:
```
✅ 분석 완료: 12개 실험
   평균: 3.8h, 중앙값: 3.5h
   범위: 2.5h ~ 5.0h
   결과 저장: stats_result.json
```

**2단계: 그래프 생성**
```bash
python .github/skills/experiment-statistics/scripts/plot_charts.py \
  --stats stats_result.json \
  --output duration_histogram.png \
  --type histogram
```

출력:
```
📊 그래프 저장: duration_histogram.png
```

### 6. 결과 정리 및 출력

**통계 요약 (stats_result.json):**
```json
{
  "count": 12,
  "mean": 3.8,
  "median": 3.5,
  "min": 2.5,
  "max": 5.0,
  "std_dev": 0.7,
  "distribution": {
    "2.0-3.0h": 3,
    "3.0-4.0h": 6,
    "4.0-5.0h": 3
  },
  "recent_experiments": [
    {"note": "20250115_001.md", "date": "2025-01-15", "value": 3.2},
    ...
  ]
}
```

**사용자에게 제시:**
```
**Golden Gate Assembly 소요 시간 통계**

📊 전체 실험 시간 (준비~완료):
- 평균: 3.8 hours
- 중앙값: 3.5 hours
- 범위: 2.5 ~ 5.0 hours
- 데이터: 12개 노트

⏱️ 반응 시간만 (Method 기준):
- 평균: 2.3 hours
- 표준 조건: 37°C 2시간, 50°C 15분

📅 최근 3회:
1. 2025-01-15: 3.2h - Note: 20250115_001.md
2. 2025-01-10: 4.0h - Note: 20250110_003.md
3. 2025-01-05: 3.5h - Note: 20250105_002.md

📊 시간 분포 그래프: [duration_histogram.png](./duration_histogram.png)
```

참고 노트 링크 제공
변동 원인 언급 (있는 경우):
- "5시간 소요 케이스는 gel purification 추가 때문"

### 6. 실험 계획 지원

사용자가 계획 중이면 권장 시간 제안:
```
평균 3.8시간이니 4시간 정도 여유있게 잡으시는 걸 추천드립니다.
```

변수 고려사항 안내:
```
샘플 수가 많으면 +30분 정도 추가 고려하세요.
```

---

## 제약 사항

- **로컬 노트 검색 결과만 사용**: 외부 표준 시간이 아닌 실제 랩 기록 기반
- **검색 범위**: ./labnotes 폴더 내 .md 파일만 검색
- **데이터 부족 시 명시**: "검색된 노트가 3개뿐이라 통계가 제한적입니다."
- **시간 형식 불일치 처리**: Duration이 없고 Time Started/Ended만 있으면 계산
- **Method 내 시간 vs 전체 시간 구분**: 사용자가 원하는 것이 무엇인지 명확히

---

## 예시

### 입력
```
사용자: PCR 얼마나 걸려?
```

### 출력 (통계 결과)
```
[로컬 노트 검색: "PCR method" - 15개 노트 발견]

**PCR 소요 시간 통계**

📊 전체 실험 시간 (준비~완료):
- 평균: 2.4 hours
- 중앙값: 2.0 hours  
- 범위: 1.5 ~ 4.0 hours
- 데이터: 15개 실험

⏱️ PCR 반응 시간만 (thermal cycler):
- 표준: 1.5 ~ 2 hours
- 프로토콜: 98°C 3min → [98°C 20s → 60°C 20s → 72°C 30s] × 30 cycles → 72°C 5min

🔍 시간 분포:
- 1.5-2h: 10건 (표준 PCR)
- 2-3h: 3건 (colony PCR 포함)
- 3-4h: 2건 (gel 전기영동 포함)

📅 최근 3회:
1. 2025-01-20: 2.0h (Note: 20250120_003)
2. 2025-01-15: 1.8h (Note: 20250115_002)
3. 2025-01-10: 2.5h (Note: 20250110_001, gel 포함)

💡 계획 권장:
- 순수 PCR: 2시간
- 결과 확인 포함: 3시간 여유
```

---

## 📜 스크립트 참조

### [analyze_stats.py](./scripts/analyze_stats.py)
통계 계산 스크립트
- Duration 파싱 (다양한 형식 지원)
- 평균, 중앙값, 표준편차 계산
- 시간 분포 분석
- 최근 실험 추출

### [plot_charts.py](./scripts/plot_charts.py)
시각화 스크립트
- 히스토그램 (시간 분포)
- 타임라인 차트 (최근 실험)
- Box plot (통계 요약)

---

## 참고 자료

- [statistics_examples.md](./examples/statistics_examples.md): 다양한 실험 통계 예시
