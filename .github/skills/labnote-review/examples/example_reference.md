## Reference 작성 예시

이 문서는 MCP 검색 결과를 바탕으로 Reference를 작성하는 다양한 예시를 보여줍니다.

---

### 예시 1: 프로토콜 최적 조건

**MCP 검색 결과:**
```
Notebook: Protocol-DB
Note: PURExpress Cell-free Expression
내용: "PURExpress 반응은 37°C에서 수행하며, 표준 반응 시간은 2-4시간입니다. 
Mg²⁺ 농도는 8-12mM 범위에서 최적 발현량을 보입니다."
```

**Reference 작성:**
```markdown
- **PURExpress 최적 반응 조건: 37°C, 2-4시간, Mg²⁺ 8-12mM** — 출처: Protocol-DB > PURExpress Cell-free Expression
```

---

### 예시 2: 형광 측정 조건

**MCP 검색 결과:**
```
Notebook: Lab-A Notebook
Note: Fluorescence Protocol
내용: "GFP 형광 측정 시 여기 파장 485nm, 방출 파장 528nm 사용. 
pH 7.4-7.6 범위 유지 필수. pH 7.0 이하에서 형광 강도 50% 이상 감소."
```

**Reference 작성:**
```markdown
- **GFP 형광 측정: Ex 485nm, Em 528nm, pH 7.4-7.6 유지 필수** — 출처: Lab-A Notebook > Fluorescence Protocol
```

---

### 예시 3: Golden Gate Assembly 사이클 조건

**MCP 검색 결과:**
```
Notebook: goldengate
Source: 978-1-0716-4220-7.pdf (Golden Gate Assembly Methods)
내용: "Golden Gate Assembly는 37°C (ligation) 2분, 16°C (digestion) 5분을 
30 cycles 반복하는 것이 표준 프로토콜입니다. 최종 80°C 10분으로 효소 불활성화."
```

**Reference 작성:**
```markdown
- **Golden Gate Assembly 사이클: 37°C 2분/16°C 5분 × 30회, 80°C 10분 종료** — 출처: goldengate > 978-1-0716-4220-7.pdf
```

---

### 예시 4: Oligo pool 농도 최적화

**MCP 검색 결과:**
```
Notebook: goldengate
Note: DNA Oligomer Assembly protocols
내용: "Oligo pool 농도를 1, 2.5, 5, 10 fmol/μL로 테스트한 결과, 
2.5 fmol/μL에서 조립 효율이 가장 높았음 (>80% assembly rate). 
5 fmol/μL 이상에서는 비특이적 결합 증가."
```

**Reference 작성:**
```markdown
- **Oligo pool 농도 최적화: 2.5 fmol/μL에서 조립 효율 최고 (>80%)** — 출처: goldengate > DNA Oligomer Assembly protocols
```

---

### 예시 5: 효소 사용법

**MCP 검색 결과:**
```
Notebook: Protocol-DB
Note: KOD polymerase manual
내용: "KOD One PCR Master Mix는 2X concentrated 형태로 제공. 
98°C 10초 denaturation, annealing 55-65°C (primer Tm 기준), 
extension 68°C 10초/kb. 30-35 cycles 권장."
```

**Reference 작성:**
```markdown
- **KOD One PCR Master Mix: 98°C 10s, 55-65°C annealing, 68°C 10s/kb, 30-35 cycles** — 출처: Protocol-DB > KOD polymerase manual
```

---

### 예시 6: Troubleshooting 정보

**MCP 검색 결과:**
```
Notebook: Troubleshooting Guide
Note: Transformation Issues
내용: "Transformation 효율이 낮을 때 확인 사항:
1) Recovery 시간 부족 (최소 1시간, SOC media)
2) Heat shock 온도/시간 부정확 (42°C 정확히 45초)
3) 세포 competency 저하 (3개월 이상 보관 시 재제작 권장)"
```

**Reference 작성:**
```markdown
- **Transformation 효율 개선: Recovery 1시간 이상, Heat shock 42°C 45초, competent cell 3개월 이내 사용** — 출처: Troubleshooting Guide > Transformation Issues
```

---

## Reference 작성 원칙

### ✅ 좋은 Reference 예시

```markdown
- **핵심 정보를 1-2줄로 요약** — 출처: 명확한 노트북명 > 노트/소스명
- **구체적 수치 포함 (온도, 시간, 농도 등)** — 출처: Protocol-DB > 실험 SOP
- **조건과 결과를 함께 기술** — 출처: Lab Notebook > 최적화 결과
```

### ❌ 피해야 할 Reference 예시

```markdown
- 프로토콜 참조 (출처 없음, 내용 모호)
- 실험 잘 됨 — 출처: 어딘가 (검증 불가능)
- 37도에서 반응함 (단위 없음, 시간 정보 없음)
- 매우 긴 설명이 여러 줄에 걸쳐 작성되어 있고 핵심을 파악하기 어려움 (너무 장황함)
```

---

## MCP 검색 결과 해석

### 검색 결과가 충분한 경우
✅ 핵심 정보 추출하여 1-2줄로 요약
✅ 출처 정보 정확히 표기
✅ 수치/조건 명시

### 검색 결과가 부족한 경우
⚠️ "검색 결과 없음. TODO: 수동 확인 필요" 명시
⚠️ 추측하지 않음
⚠️ 사용자에게 추가 정보 요청

### 검색 결과가 불명확한 경우
🔍 사용자에게 확인 요청
🔍 여러 검색 결과 중 가장 관련성 높은 것 선택
🔍 불확실성 표시 ("추정", "가능성")
