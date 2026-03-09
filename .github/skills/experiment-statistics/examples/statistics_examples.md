## Experiment Time Statistics 예시

이 문서는 다양한 실험 시간 통계 시나리오와 예상 출력을 보여줍니다.

---

### 시나리오 1: PCR 시간 통계

**사용자 요청:**
```
PCR 얼마나 걸려?
```

**MCP 검색 및 분석:**
- 검색 쿼리: "PCR method protocol"
- 15개 노트 발견
- Time Started/Ended, Duration 데이터 추출
- 통계 계산

**출력:**
```
**PCR 소요 시간 통계**

📊 전체 실험 시간 (준비~완료):
- 평균: 2.4 hours
- 중앙값: 2.0 hours  
- 범위: 1.5 ~ 4.0 hours
- 표준편차: 0.6 hours
- 데이터: 15개 실험

⏱️ PCR 반응 시간만 (thermal cycler):
- 표준: 1.5 ~ 2.0 hours
- 프로토콜: 98°C 3min → [98°C 20s → 60°C 20s → 72°C 30s] × 30 cycles → 72°C 5min

🔍 시간 분포:
- 1.5-2.0h: 10건 (표준 PCR)
- 2.0-3.0h: 3건 (colony PCR 포함)
- 3.0-4.0h: 2건 (gel 전기영동 포함)

📅 최근 5회:
1. 2025-01-20: 2.0h - Note: 20250120_003_pcr.md
2. 2025-01-18: 1.8h - Note: 20250118_002_pcr.md
3. 2025-01-15: 2.5h - Note: 20250115_001_colony_pcr.md (gel 포함)
4. 2025-01-12: 1.9h - Note: 20250112_004_pcr.md
5. 2025-01-10: 2.2h - Note: 20250110_002_pcr.md

💡 계획 권장:
- 순수 PCR: 2시간
- 결과 확인 포함 (gel): 3시간 여유
- 샘플 수가 많으면 (>24개) +30분 추가 고려
```

---

### 시나리오 2: Golden Gate Assembly 시간 통계

**사용자 요청:**
```
Golden Gate Assembly 평균 시간 알려줘
```

**MCP 검색 및 분석:**
- 검색 쿼리: "Golden Gate Assembly method protocol"
- 12개 노트 발견
- Duration 데이터 추출 및 분석

**출력:**
```
**Golden Gate Assembly 소요 시간 통계**

📊 전체 실험 시간 (준비~완료):
- 평균: 3.8 hours
- 중앙값: 3.5 hours
- 범위: 2.5 ~ 5.0 hours
- 표준편차: 0.7 hours
- 데이터: 12개 노트

⏱️ 반응 시간만 (Method 기준):
- 평균: 2.3 hours
- 표준 조건: 37°C 2분/16°C 5분 × 30 cycles
- 변동 범위: 2.0 ~ 2.5 hours

🔍 시간 분포:
- 2.5-3.0h: 3건 (반응만)
- 3.0-4.0h: 6건 (표준 workflow)
- 4.0-5.0h: 3건 (gel purification 포함)

📅 최근 3회:
1. 2025-01-15: 3.2h - Note: 20250115_001_goldengate.md
2. 2025-01-10: 4.0h - Note: 20250110_003_goldengate.md (gel 포함)
3. 2025-01-05: 3.5h - Note: 20250105_002_goldengate.md

⚙️ 시간 변동 요인:
- +0.5h: Gel purification 추가 시
- +1.0h: Colony PCR screening 포함 시
- -0.3h: Pre-made reaction mix 사용 시

💡 계획 권장:
- 표준 workflow: 4시간 여유 권장
- Fragment 수 >4개: +30분 추가
- 첫 시도: 5시간 여유 (troubleshooting 대비)
```

---

### 시나리오 3: Transformation 시간 통계

**사용자 요청:**
```
Transformation 시간 통계 보여줘
```

**MCP 검색 및 분석:**
- 검색 쿼리: "transformation method protocol competent cell"
- 18개 노트 발견
- Time Started/Ended 데이터 분석

**출력:**
```
**Transformation 소요 시간 통계**

📊 전체 실험 시간 (준비~plating):
- 평균: 1.8 hours
- 중앙값: 1.5 hours
- 범위: 1.0 ~ 3.0 hours
- 표준편차: 0.5 hours
- 데이터: 18개 실험

⏱️ 단계별 시간:
- Heat shock: 45 seconds
- Recovery (37°C): 1.0 hour (표준)
- Plating & spreading: 5-10 minutes
- Overnight incubation: 12-16 hours (별도)

🔍 시간 분포:
- 1.0-1.5h: 8건 (표준 protocol)
- 1.5-2.0h: 7건 (샘플 수 많음)
- 2.0-3.0h: 3건 (colony PCR screening 포함)

📅 최근 5회:
1. 2025-01-22: 1.3h - Note: 20250122_001_transformation.md
2. 2025-01-18: 1.5h - Note: 20250118_001_transformation.md
3. 2025-01-15: 2.5h - Note: 20250115_003_transformation.md (screening 포함)
4. 2025-01-12: 1.6h - Note: 20250112_002_transformation.md
5. 2025-01-08: 1.4h - Note: 20250108_001_transformation.md

⚙️ 효율성 팁:
- Recovery 시간: 최소 1시간, 최대 2시간
- 샘플 수 >10개: batch processing으로 +20분
- Pre-warmed SOC media 사용: -10분

💡 계획 권장:
- 표준: 2시간 (recovery 포함)
- 결과 확인까지: 14-18시간 (overnight 포함)
- 고효율 필요 시: 2시간 recovery 권장
```

---

### 시나리오 4: 전체 Workflow 시간 통계

**사용자 요청:**
```
WB010 DNA Oligomer Assembly workflow 전체 시간 알려줘
```

**MCP 검색 및 분석:**
- 검색 쿼리: "WB010 DNA Oligomer Assembly workflow"
- 8개 workflow 노트 발견
- 각 Unit Operation별 시간 합산

**출력:**
```
**WB010 DNA Oligomer Assembly Workflow 소요 시간 통계**

📊 전체 Workflow 시간:
- 평균: 5.2 hours
- 중앙값: 5.0 hours
- 범위: 4.0 ~ 7.0 hours
- 데이터: 8개 workflow

⏱️ Unit Operation별 시간 (평균):

1️⃣ **UHW010 Liquid Handling** (Assembly PCR prep)
   - 평균: 0.5 hours
   - 범위: 0.3 ~ 0.8 hours

2️⃣ **UHW100 Thermocycling** (Assembly PCR)
   - 평균: 1.5 hours
   - 범위: 1.3 ~ 1.8 hours

3️⃣ **UHW230 Fragment Analysis** (Gel check)
   - 평균: 0.3 hours
   - 범위: 0.2 ~ 0.5 hours

4️⃣ **UHW180 Incubation** (Error-Correction)
   - 평균: 0.5 hours
   - 범위: 0.3 ~ 1.0 hours

5️⃣ **UHW100 Thermocycling** (Recovery PCR)
   - 평균: 1.5 hours
   - 범위: 1.3 ~ 1.8 hours

6️⃣ **UHW230 Fragment Analysis** (Final check)
   - 평균: 0.3 hours
   - 범위: 0.2 ~ 0.5 hours

7️⃣ **Optional: Gel Purification**
   - 평균: +0.8 hours (5/8 케이스에서 수행)

🔍 시간 분포:
- 4.0-5.0h: 3건 (최적화된 workflow)
- 5.0-6.0h: 4건 (표준 workflow)
- 6.0-7.0h: 1건 (gel purification 포함)

📅 최근 3회:
1. 2025-01-15: 5.1h - Note: 20250115_001_WB010.md
2. 2025-01-10: 4.8h - Note: 20250110_002_WB010.md
3. 2025-01-05: 5.5h - Note: 20250105_001_WB010.md

⚙️ 시간 단축 팁:
- Pre-mix 준비: -15분
- Parallel processing (gel 동시 진행): -30분
- Error-Correction 생략 (high-quality oligo): -30분

💡 계획 권장:
- 표준 실행: 6시간 여유
- 첫 시도: 7시간 여유 (troubleshooting 대비)
- 최적화 후: 4.5-5시간 가능
```

---

### 시나리오 5: 데이터 부족 케이스

**사용자 요청:**
```
Cell-free protein expression 시간 알려줘
```

**MCP 검색 및 분석:**
- 검색 쿼리: "cell-free protein expression method"
- 3개 노트만 발견 (데이터 부족)

**출력:**
```
**Cell-free Protein Expression 소요 시간 통계**

⚠️ 데이터 제한: 검색된 노트가 3개뿐이라 통계가 제한적입니다.

📊 현재 데이터 (3개 실험):
- 평균: 3.2 hours
- 범위: 2.5 ~ 4.0 hours
- 데이터: 3개 노트 (통계적 신뢰도 낮음)

📅 기록된 실험:
1. 2025-01-10: 2.5h - Note: 20250110_001_cellfree.md
   - PURExpress, 2시간 반응, 1회 sampling
2. 2024-12-15: 3.5h - Note: 20241215_002_cellfree.md
   - PURExpress, 3시간 반응, 3회 sampling
3. 2024-11-20: 4.0h - Note: 20241120_001_cellfree.md
   - Custom cell-free system, 4시간 반응, 1회 sampling

⏱️ 반응 시간 (Protocol 기준):
- PURExpress: 2-3시간 (표준)
- Custom system: 3-4시간

💡 권장 사항:
- 더 정확한 통계를 위해 최소 10개 이상의 실험 데이터 필요
- 표준 PURExpress protocol 기준 3-4시간 여유 권장
- 첫 시도: 5시간 여유 (최적화 필요 고려)

🔍 추가 검색 제안:
- "PURExpress protocol" 검색으로 external protocol 확인
- 다른 랩의 cell-free expression 노트 참고 필요
```

---

## 통계 분석 원칙

### 데이터가 충분한 경우 (N ≥ 10)
✅ 평균, 중앙값, 표준편차 제공
✅ 시간 분포 분석
✅ 최근 이력 및 추세 파악

### 데이터가 부족한 경우 (N < 10)
⚠️ 데이터 부족 명시
⚠️ 신뢰도 낮음 표시
⚠️ 추가 데이터 수집 권장

### 시간 변동이 큰 경우
🔍 변동 원인 분석
🔍 조건별 분류 (표준/옵션 포함 등)
🔍 이상치 확인 및 설명
