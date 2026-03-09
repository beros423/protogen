## Multiple UO Workflow Example: WB010 DNA Oligomer Assembly

이 예시는 여러 Unit Operations가 순차적으로 연결된 Workflow 형태의 연구노트 구조를 보여줍니다.

```markdown
---
title: WB010 DNA Oligomer Assembly - sfGFP-mCherry oligomer assembly test
experimenter: John Doe
created_date: 2025-01-15
end_date: 2025-01-15
last_updated_date: 2025-01-15
Sample Tracking: Yes
---

## [WB010 DNA Oligomer Assembly] sfGFP-mCherry oligomer assembly test
> Oligo pool로부터 sfGFP와 mCherry 유전자를 조립하는 실험

## 🗂️ Related Unit Operations
- [UHW010 Liquid Handling - Assembly PCR prep](#uhw010-liquid-handling-assembly-pcr-prep)
- [UHW100 Thermocycling - Assembly PCR](#uhw100-thermocycling-assembly-pcr)
- [UHW230 Fragment Analysis - PCR product check](#uhw230-fragment-analysis-pcr-product-check)

---

### [UHW010 Liquid Handling] Assembly PCR reaction mixture preparation

- **Description**: Oligo pool과 KOD One PCR Master Mix를 사용하여 Assembly PCR 반응액 준비

#### Meta
- Experimenter: John Doe
- Start_date: 2025-01-15 10:00
- End_date: 2025-01-15 10:30
- Duration: 0.5 hours

#### Input
- Oligo pool: sfGFP_pool (500 fmol/μL), mCherry_pool (500 fmol/μL)
- KOD One PCR Master Mix (Toyobo)

#### Reagent
- KOD One PCR Master Mix: 2X concentrated

#### Consumables
- PCR tubes (0.2 mL, 6 tubes)
- Pipette tips

#### Equipment
- Pipette set (P2, P10, P20, P200)

#### Method
1. 2가지 oligo pool 농도 조건 설정:
   - Condition 1: 2.5 fmol/μL (최적 조건)
   - Condition 2: 5.0 fmol/μL (비교 조건)
2. 각 조건별 3개 반응 준비 (총 6 tubes)
3. Reaction mixture 구성 (10 μL per tube):
   - KOD One Master Mix: 5 μL
   - Oligo pool: 1 μL (희석)
   - Water: 4 μL

#### Output
- Assembly PCR reaction mixture, 10 μL per tube × 6 tubes

#### Results & Discussions
- 총 2가지 oligo pool 농도 조건으로 준비하였다.
- 각 조건별 3 replicates 구성

#### Reference
- **Oligo pool 농도 최적화: 2.5 fmol/μL에서 조립 효율 최고** — 출처: goldengate > DNA Oligomer Assembly protocols
- **KOD One PCR Master Mix 최적 조건: 98°C denaturation, 30 cycles** — 출처: Protocol-DB > KOD polymerase manual

---

### [UHW100 Thermocycling] Assembly PCR reaction

- **Description**: Thermocycler를 사용하여 oligo assembly 반응 수행

#### Meta
- Experimenter: John Doe
- Start_date: 2025-01-15 10:30
- End_date: 2025-01-15 12:00
- Duration: 1.5 hours

#### Input
- Assembly PCR reaction mixture (from previous step, PCR tube, 10 μL per tube)

#### Reagent
- None (모두 이전 단계에서 준비됨)

#### Consumables
- None

#### Equipment
- Thermocycler (Applied Biosystems Veriti)

#### Method
1. Thermocycler 프로그램 설정:
   - 98°C 10 seconds
   - 55°C 5 seconds
   - 68°C 10 seconds (30 cycles)
   - 4°C hold
2. PCR tube를 thermocycler에 배치
3. 프로그램 실행

#### Output
- Assembly PCR products (PCR tube, 10 μL per tube)

#### Results & Discussions
- 설정된 사이클 조건에 따라 반응을 성공적으로 수행하였다.
- 예상 반응 시간 1.5시간

#### Reference
- **Assembly PCR cycling: 98°C 10s → 55°C 5s → 68°C 10s/kb × 30 cycles** — 출처: goldengate > 978-1-0716-4220-7.pdf

---

### [UHW230 Nucleic Acid Fragment Analysis] PCR product verification

- **Description**: E-gel을 사용하여 Assembly PCR 산물의 크기 확인

#### Meta
- Experimenter: John Doe
- Start_date: 2025-01-15 12:00
- End_date: 2025-01-15 12:20
- Duration: 0.33 hours

#### Input
- Assembly PCR products (from previous step, 2 μL per sample)
- 1kb DNA ladder

#### Reagent
- E-Gel EX 2% Agarose Gel

#### Consumables
- Pipette tips

#### Equipment
- E-Gel Power Snap Electrophoresis Device

#### Method
1. E-gel을 장비에 장착
2. 각 샘플 2 μL씩 loading
3. DNA ladder 2 μL loading
4. 10분간 전기영동 실행
5. UV로 결과 확인

#### Output
- Gel image (saved as image file)
- Verified PCR products: sfGFP (~750 bp), mCherry (~700 bp)

#### Results & Discussions
- 두 조건 모두 예상 크기의 밴드 확인
- Condition 1 (2.5 fmol/μL)에서 더 강한 밴드 관찰
- 비특이적 증폭 없음

#### Reference
- **E-gel 사용법: 2% agarose, 10분 전기영동 표준 조건** — 출처: E-Gel Manual > Quick Protocol
- **DNA ladder 사용: 1kb ladder, 2 μL 권장** — 출처: Lab-Protocol > Gel Electrophoresis

---

### Workflow Summary

✅ 전체 소요 시간: 2.33 hours
✅ 성공적으로 sfGFP와 mCherry Assembly PCR 완료
✅ Condition 1 (2.5 fmol/μL)이 최적 조건으로 확인됨

### Next Steps
- Recovery PCR 수행
- Plasmid cloning 진행
```

## 주요 특징

### 1. Workflow 메타데이터
- title, experimenter, created_date, end_date 등 전체 workflow 정보

### 2. Related Unit Operations 목차
- 각 UO로 빠르게 이동할 수 있는 링크 제공

### 3. UO별 독립적 구조
- 각 UO마다 Meta, Input, Reagent, Method, Output, Results & Discussions 섹션 보유
- 각 UO 마지막에 개별 Reference 섹션

### 4. UO 간 연결
- 이전 UO의 Output → 다음 UO의 Input
- "from previous step" 명시로 흐름 명확화

### 5. Workflow Summary
- 전체 실험의 성과와 다음 단계 제시
