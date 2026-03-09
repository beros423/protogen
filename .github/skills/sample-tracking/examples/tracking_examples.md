## Sample Tracking 예시

이 문서는 다양한 샘플 추적 시나리오와 예상 출력을 보여줍니다.

---

### 시나리오 1: 출처 추적 (Source Tree)

**사용자 요청:**
```
DNA-20250115-001의 출처를 알려줘
```

**MCP 검색 및 분석:**
1. Output에 DNA-20250115-001이 있는 노트 검색 → 2025-01-15 Golden Gate Assembly 노트 발견
2. 해당 노트의 Input 확인:
   - Fragment-1: DNA-20250110-005
   - Fragment-2: DNA-20250110-006
   - Fragment-3: DNA-20250112-002
   - Vector: pET-28a(+)
3. 각 Fragment의 출처 재귀적 추적

**출력:**
```
**DNA-20250115-001 출처 추적**

📦 제작 방법: Golden Gate Assembly (2025-01-15)

🌳 Source Tree:
DNA-20250115-001 (Golden Gate Assembly 산물)
├─ DNA-20250110-005 (Fragment-1, PCR product)
│  ├─ Template: Plasmid-20241220-003
│  └─ Primers: Primer-001, Primer-002
├─ DNA-20250110-006 (Fragment-2, PCR product)
│  ├─ Template: Genomic DNA (E. coli K12)
│  └─ Primers: Primer-003, Primer-004
├─ DNA-20250112-002 (Fragment-3, gene synthesis)
│  └─ Source: IDT gBlock synthesis
└─ Vector: pET-28a(+) (commercial)

📅 제작 경로:
1. 2024-12-20: Primer 설계 및 주문
2. 2025-01-10: Fragment-1, 2 PCR 증폭
3. 2025-01-12: Fragment-3 수령 (IDT)
4. 2025-01-15: Golden Gate Assembly

📝 관련 노트:
- 20250115_001_goldengate.md
- 20250110_003_pcr_fragment.md
- 20250112_001_gblock.md
```

---

### 시나리오 2: 사용 이력 (Usage History)

**사용자 요청:**
```
DNA-20250115-001이 어디에 사용되었는지 알려줘
```

**MCP 검색 및 분석:**
1. Input에 DNA-20250115-001이 있는 노트 검색
2. 시간순 정렬

**출력:**
```
**DNA-20250115-001 사용 이력**

📊 총 4회 사용됨

1️⃣ **2025-01-16**: Sequencing verification
   - 사용량: 2 μL
   - 실험: Plasmid sequence confirmation
   - 노트: 20250116_002_sequencing.md
   - 결과: ✅ Sequence confirmed

2️⃣ **2025-01-18**: Transformation (BL21(DE3))
   - 사용량: 5 μL
   - 실험: Protein expression strain construction
   - 노트: 20250118_001_transformation.md
   - 결과: ✅ ~200 colonies

3️⃣ **2025-01-20**: Restriction analysis
   - 사용량: 3 μL
   - 실험: Plasmid map verification
   - 노트: 20250120_003_restriction.md
   - 결과: ✅ Expected bands

4️⃣ **2025-01-22**: Stock preparation
   - 사용량: 10 μL
   - 실험: Glycerol stock for long-term storage
   - 노트: 20250122_001_stock.md
   - 결과: ✅ Stored at -80°C

💡 최근 사용: 2025-01-22 (3일 전)
```

---

### 시나리오 3: 파생 샘플 (Derived Samples)

**사용자 요청:**
```
DNA-20250115-001로 만든 다른 샘플들 보여줘
```

**MCP 검색 및 분석:**
1. Input에 DNA-20250115-001이 있는 노트 찾기
2. 각 노트의 Output 섹션 확인

**출력:**
```
**DNA-20250115-001로부터 제작된 샘플**

🧬 총 3가지 파생 샘플

1️⃣ **Strain-20250118-005** (E. coli BL21(DE3) transformant)
   - 제작 일자: 2025-01-18
   - 실험: Transformation
   - 특징: Protein expression strain
   - 노트: 20250118_001_transformation.md

2️⃣ **DNA-20250120-008** (Linearized plasmid)
   - 제작 일자: 2025-01-20
   - 실험: Restriction digestion with NdeI/XhoI
   - 용도: Insert isolation for sub-cloning
   - 노트: 20250120_003_restriction.md

3️⃣ **Stock-20250122-001** (Glycerol stock)
   - 제작 일자: 2025-01-22
   - 실험: Long-term storage preparation
   - 보관 위치: -80°C freezer, Box-A, Position A1
   - 노트: 20250122_001_stock.md

📈 파생 경로:
DNA-20250115-001
├─ Strain-20250118-005 (transformation)
├─ DNA-20250120-008 (digestion)
└─ Stock-20250122-001 (storage)
```

---

### 시나리오 4: 용량 추적 (Volume Tracking)

**사용자 요청:**
```
DNA-20250115-001 용량 알려줘
```

**MCP 검색 및 분석:**
1. Output에서 초기 제작량 확인
2. 각 사용 기록에서 사용량 확인
3. 남은 용량 계산

**출력:**
```
**DNA-20250115-001 용량 추적**

📅 제작: 2025-01-15
- 제작량: 50 μL (Golden Gate Assembly 산물)
- 농도: ~100 ng/μL (추정)
- 출처: Lab Note 20250115_001_goldengate.md

📊 사용 이력:
1. 2025-01-16: Sequencing (2 μL)
2. 2025-01-18: Transformation (5 μL)
3. 2025-01-20: Restriction (3 μL)
4. 2025-01-22: Stock (10 μL)

💧 용량 계산:
- 제작량: 50 μL
- 총 사용량: 20 μL
- **남은 용량: ~30 μL (추정)**

⚠️ 주의사항:
- 증발/피펫팅 손실 미고려 (~5% 예상)
- 실제 남은 용량: 28-30 μL 추정
- 권장: 주기적 재측정

💡 권장 사항:
- 남은 용량으로 약 10-15회 추가 실험 가능 (샘플당 2 μL 기준)
- 5 μL 이하로 줄어들면 백업 제작 권장
```

---

### 시나리오 5: 전체 타임라인

**사용자 요청:**
```
DNA-20250115-001의 전체 타임라인 보여줘
```

**출력:**
```
**DNA-20250115-001 전체 타임라인**

📅 2025-01-15 (Day 0) - 제작
   🧬 Golden Gate Assembly
   - Input: Fragment-1, 2, 3 + pET-28a(+)
   - Output: 50 μL, ~100 ng/μL
   - 노트: 20250115_001_goldengate.md

📅 2025-01-16 (Day 1) - 검증
   🔍 Sequencing verification
   - 사용량: 2 μL
   - 결과: ✅ Sequence confirmed
   - 노트: 20250116_002_sequencing.md

📅 2025-01-18 (Day 3) - 활용 1
   🦠 Transformation to BL21(DE3)
   - 사용량: 5 μL
   - 파생: Strain-20250118-005
   - 노트: 20250118_001_transformation.md

📅 2025-01-20 (Day 5) - 분석
   ✂️ Restriction analysis
   - 사용량: 3 μL
   - 파생: DNA-20250120-008 (linearized)
   - 노트: 20250120_003_restriction.md

📅 2025-01-22 (Day 7) - 보관
   🧊 Glycerol stock preparation
   - 사용량: 10 μL
   - 파생: Stock-20250122-001
   - 위치: -80°C, Box-A, A1
   - 노트: 20250122_001_stock.md

📊 요약:
- 총 사용 기간: 7일
- 총 사용량: 20 μL (40%)
- 남은 용량: ~30 μL (60%)
- 파생 샘플: 3개
- 상태: ✅ Active (최근 사용 3일 전)
```

---

## 추적 시 고려사항

### 데이터가 완전한 경우
✅ 정확한 용량 계산 제공
✅ 모든 사용처 리스트
✅ 명확한 Source Tree

### 데이터가 불완전한 경우
⚠️ 누락 정보 명시
⚠️ 추정값 표시
⚠️ 사용자에게 확인 권장

```
⚠️ 2025-01-20 노트에서 정확한 사용량 정보가 없습니다.
💡 해당 노트를 업데이트하시겠어요?
```
