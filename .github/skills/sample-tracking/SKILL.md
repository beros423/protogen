---
name: sample-tracking
description: Track K-BioFoundry sample IDs through local lab notes (./labnotes) using file search. Provides source tree, usage history, derived samples, volume tracking, and timeline analysis. Use when user asks about sample origins, usage, remaining volume, or tracking history.
---

# K-BioFoundry Sample ID Tracking

이 skill은 Sample ID를 기반으로 로컬 labnotes 폴더의 연구노트를 검색하여 샘플의 출처, 사용 이력, 파생 샘플, 용량 등을 추적합니다.

## 주요 기능

1. **샘플 출처 (Source Tree)**: 샘플이 어떻게 만들어졌는지 추적
2. **사용 이력 (Usage History)**: 샘플이 어디에 사용되었는지 시간순 정리
3. **파생 샘플 (Derived Samples)**: 이 샘플을 Input으로 만든 다른 샘플들 리스트
4. **용량 추적 (Volume Tracking)**: 제작량, 사용량, 남은 용량 계산
5. **전체 타임라인**: 제작부터 현재까지 모든 이력

## 사용 시점

- "DNA-20250101-001 출처 알려줘"
- "이 샘플 얼마나 남았어?"
- "샘플 사용 이력 보여줘"
- 특정 Sample ID에 대한 추적 요청

---

## 작업 절차

### 1. 사용자 의도 명확화

사용자가 요청한 내용이 불분명하면 반드시 되물어서 확인합니다.

추적 가능한 정보 유형 (예시, 이에 국한되지 않음):
- 📦 **샘플 출처 (Source Tree)**: 이 샘플이 어떻게 만들어졌는지?
- 📊 **사용 이력 (Usage History)**: 이 샘플이 어디에 사용되었는지?
- 🧬 **파생 샘플 (Derived Samples)**: 이 샘플을 Input으로 만든 다른 샘플들은?
- 💧 **용량 추적 (Volume Tracking)**: 제작 용량, 사용량, 남은 용량은?
- 📅 **제작/사용 일자**: 언제 만들어졌고, 언제 사용되었는지?
- 🔍 **특정 기간 필터링**: 특정 날짜 이후/이전 사용처는?
- 📈 **전체 타임라인**: 제작부터 현재까지 모든 이력

예시 질문 (개방형):
```
DNA-20250101-001에 대해 어떤 정보가 필요하신가요?

예를 들어:
- 출처 (어떻게 만들어졌는지)
- 사용 이력 (어디에 사용되었는지)
- 파생 샘플 (이 샘플로 만든 다른 샘플들)
- 용량 (제작량, 사용량, 남은 양)
- 전체 타임라인
- 또는 다른 특정 정보

구체적으로 알려주세요!
```

### 2. 로컬 노트 검색 수행

Sample ID로 관련 노트 검색 (./labnotes 폴더):
```
# grep_search 사용
query: "DNA-20250101-001"
isRegexp: false
includePattern: "labnotes/**/*.md"
```

또는 semantic_search 사용:
```
query: "DNA-20250101-001 sample output input"
```

- Output 섹션에서 샘플 생성 기록 찾기
- Input 섹션에서 샘플 사용 기록 찾기

### 3. 데이터 수집 및 분석

#### A. 출처 추적 (Source Tree)
- Output에 해당 샘플이 있는 노트 찾기 → 제작 일자, 제작 방법 확인
- 그 노트의 Input 확인 → 부모 샘플들 추적
- 재귀적으로 상위 샘플들의 출처 추적
- 트리 구조로 정리:

```
DNA-20250101-001 (2025-01-01 제작)
├─ DNA-20241220-005 (primer)
├─ DNA-20241215-003 (template)
└─ Reagent: Phusion polymerase
```

#### B. 사용 이력 (Usage History)
- Input에 해당 샘플이 있는 노트 찾기 → 사용 일자, 실험명, 사용량 확인
- 시간순으로 정렬하여 리스트 작성:

```
DNA-20250101-001 사용 이력:
1. 2025-01-05: Golden Gate Assembly (5 μL 사용)
2. 2025-01-10: Sequencing (1 μL 사용)
3. 2025-01-15: Transformation (2 μL 사용)
```

#### C. 파생 샘플 (Derived Samples)
- Input에 해당 샘플이 있는 노트 찾기 → Output 섹션 확인
- 해당 샘플로부터 만들어진 새로운 샘플들 리스트:

```
DNA-20250101-001로부터 제작된 샘플:
1. Plasmid-20250105-001 (Golden Gate Assembly)
2. Strain-20250110-002 (Transformation 결과)
3. DNA-20250115-005 (PCR 증폭 산물)
```

#### D. 용량 추적 (Volume Tracking)
- 제작 노트의 Output에서 초기 용량 확인
- 각 사용 노트의 Input/Method에서 사용량 확인
- 남은 용량 계산:

```
DNA-20250101-001 용량:
- 제작량: 50 μL (2025-01-01)
- 사용량: 8 μL (총 3회 사용)
- 남은 용량: 42 μL (추정)
```

#### E. 특정 기간 필터링
- 검색된 노트의 날짜 확인
- 사용자가 지정한 기간 내 노트만 필터링
- 기간 내 사용 이력만 보고

### 4. Python 스크립트로 추적 분석

#### 데이터 준비

검색/추출된 노트 데이터를 JSON 형식으로 정리:
```json
[
  {
    "file": "20250115_001.md",
    "date": "2025-01-15",
    "outputs": ["DNA-20250115-001: 50 μL"],
    "inputs": ["DNA-20250110-005", "DNA-20250110-006"]
  },
  {
    "file": "20250116_002.md",
    "date": "2025-01-16",
    "outputs": [],
    "inputs": ["DNA-20250115-001: 2 μL"]
  },
  ...
]
```

#### 스크립트 실행

**샘플 추적 (전체 정보):**
```bash
python .github/skills/sample-tracking/scripts/track_sample.py \
  --data notes_data.json \
  --sample-id DNA-20250115-001 \
  --output tracking_result.json \
  --mode all
```

**특정 정보만 추출:**
```bash
# 출처 트리만
python track_sample.py --data notes_data.json --sample-id DNA-20250115-001 --mode source

# 사용 이력만
python track_sample.py --data notes_data.json --sample-id DNA-20250115-001 --mode usage

# 용량 계산만
python track_sample.py --data notes_data.json --sample-id DNA-20250115-001 --mode volume
```

**출력 예시:**
```
✅ 추적 완료: DNA-20250115-001
   결과 저장: tracking_result.json
```

#### 용량 계산 유틸리티

**희석 계산:**
```python
from volume_calculator import ConcentrationCalculator

dilution = ConcentrationCalculator.calculate_dilution(
    initial_conc="100 ng/μL",
    target_conc="20 ng/μL",
    final_volume_str="50 μL"
)
print(dilution)
# {'sample_volume': '10.0 μL', 'diluent_volume': '40.0 μL', 'final_volume': '50.0 μL'}
```

### 5. 결과 정리 및 출력

**추적 결과 (tracking_result.json):**
```json
{
  "sample_id": "DNA-20250115-001",
  "source_tree": {
    "sample_id": "DNA-20250115-001",
    "created_date": "2025-01-15",
    "created_in": "20250115_001.md",
    "volume": "50 μL",
    "parents": [
      {"sample_id": "DNA-20250110-005", ...},
      {"sample_id": "DNA-20250110-006", ...}
    ]
  },
  "usage_history": [...],
  "volume_tracking": {
    "initial_volume": "50 μL",
    "total_used": "8 μL",
    "remaining": "42 μL",
    "usage_breakdown": [...]
  }
}
```

**사용자에게 제시:**
- 요청 유형에 맞춰 정보 구조화
- 출처/날짜/용량 등 핵심 정보만 간결하게 제시
- 누락된 정보가 있으면 명시:
  - 예: "⚠️ 2025-01-05 노트에서 사용량 정보가 없습니다."
- 불확실한 계산이 있으면 표시:
  - 예: "💧 남은 용량 ~40 μL (추정값, 증발/손실 미고려)"

### 5. 사용자 확인 및 후속 작업 제안

- 추가로 확인이 필요한 사항 알림
- 관련 노트 링크 제공
- 다음 액션 제안:
  - "이 샘플을 계속 추적하려면 노트에 용량 기록을 추가하시겠어요?"
  - "부족한 정보는 해당 노트를 업데이트하시겠어요?"

---

## 제약 사항

- **로컬 노트 검색 결과만 사용**: 용량/날짜 등을 추측하지 않음
- **검색 범위**: ./labnotes 폴더 내 .md 파일만 검색
- **불확실성 명시**: 정보가 불완전하면 "추정", "확인 필요" 표시
- **사용자 의도 우선**: 모호한 요청은 반드시 되물어서 명확히 함
- **날짜 기준 정렬**: 이력은 시간순으로 정렬하여 제시

---

## 예시

### 입력
```
사용자: DNA-20250101-001 추적해줘
```

### 출력 (의도 확인)
```
DNA-20250101-001에 대해 어떤 정보가 필요하신가요?

예를 들어:
- 출처 (어떻게 만들어졌는지)
- 사용 이력 (어디에 사용되었는지)
- 파생 샘플 (이 샘플로 만든 다른 샘플들)
- 용량 (제작량, 사용량, 남은 양)
- 전체 타임라인
- 또는 다른 특정 정보

구체적으로 알려주세요!
```

### 입력
```
사용자: 용량 알려줘
```

### 출력 (용량 추적 결과)
```
[로컬 노트 검색 수행...]

**DNA-20250101-001 용량 추적**

📅 제작: 2025-01-01
- 제작량: 50 μL (Golden Gate Assembly 산물)
- 출처: Lab Note 20250101_001_goldengate

📊 사용 이력:
1. 2025-01-05: Sequencing (1 μL) - Note 20250105_002
2. 2025-01-10: Transformation (5 μL) - Note 20250110_003
3. 2025-01-15: PCR template (2 μL) - Note 20250115_001

💧 용량 계산:
- 제작량: 50 μL
- 총 사용량: 8 μL
- **남은 용량: ~42 μL (추정)**

⚠️ 주의사항:
- 증발/피펫팅 손실 미고려
- 2025-01-10 노트에서 정확한 사용량 확인 권장
```

---

## 📜 스크립트 참조

### [track_sample.py](./scripts/track_sample.py)
샘플 추적 메인 스크립트
- Sample ID 추출 및 인덱싱
- 출처 트리 재귀 생성
- 사용 이력 시간순 정렬
- 파생 샘플 추출
- 용량 계산

### [volume_calculator.py](./scripts/volume_calculator.py)
용량 계산 유틸리티
- 단위 변환 (μL, mL, L)
- 총 질량 계산 (농도 × 용량)
- 희석 계산 (C1V1 = C2V2)
- 질량 단위 변환 (ng, μg, mg)

---

## 참고 자료

- [tracking_examples.md](./examples/tracking_examples.md): 다양한 추적 시나리오 예시
