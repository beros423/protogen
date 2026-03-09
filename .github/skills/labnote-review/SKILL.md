---
name: labnote-review
description: Review K-BioFoundry lab notes, validate template format, check UO workflow consistency, and add MCP-sourced references to each Unit Operation section. Use when user asks to review notes, add references, or verify note structure.
---

# K-BioFoundry Lab Note Review & Reference Addition

이 skill은 K-BioFoundry 연구노트를 검토하고, MCP 검색을 통해 각 Unit Operation에 대한 Reference를 추가합니다.

## 주요 기능

1. **템플릿 형식 검증**: [labnote_template.md](./labnote_template.md) 기준으로 필수 섹션 확인
2. **이전/이후 노트와 일관성 확인**: MCP로 같은 프로젝트의 연구노트 검색 및 비교
3. **Unit Operation 흐름 검토**: Multiple UO Workflow의 Input/Output 호환성 검증
4. **MCP 기반 Reference 추가**: 각 UO별로 관련 자료를 검색하여 Reference 섹션 작성

## 사용 시점

- 사용자가 "노트 검토해줘", "reference 추가해줘" 요청 시
- 연구노트 파일을 열고 검증이 필요한 경우
- Workflow 내 UO 흐름 검증이 필요한 경우

---

## 작업 절차

### 1. 노트 파일 읽기
- 사용자가 지정한 또는 현재 열린 노트 파일 전체 내용 읽기
- Methods, 이론적 배경, 실험 조건 등 핵심 요소 파악

### 2. 템플릿 형식 검증
- `labnote_template.md` 파일을 읽어 표준 형식 확인
- 현재 노트와 템플릿 비교:
  - 필수 섹션 누락 여부 확인 (Meta, Method, Input, Output, Result, Conclusion 등)
  - 필수 메타데이터 누락 확인 (Title, Date, Objective 등)
- **부족한 부분 발견 시**: 사용자에게 명확히 알리고 추가 여부 확인
  - 예: "⚠️ Input 섹션이 누락되었습니다. 추가할까요?"

### 3. 이전/이후 노트와 일관성 확인
- MCP로 같은 프로젝트의 이전/이후 연구노트 검색
- 검색 쿼리: `"{프로젝트명 또는 실험명} previous recent notes"`
- 비교 대상:
  - Methods의 프로토콜 변경 사항
  - Input 샘플 ID의 연결성 (이전 Output → 현재 Input)
  - Output 명명 규칙 일관성
- **차이 발견 시**: 사용자에게 확인 요청
  - 예: "🔍 이전 노트에서는 37°C 2시간이었는데, 지금은 4시간으로 변경되었습니다. 의도적인 변경인가요?"

### 4. Unit Operation 흐름 검토 (Input/Output 호환성)

#### 노트 유형 판별
- **Single UO**: 하나의 UO만 있는 단일 실험
- **Multiple UO**: 여러 UO가 순차적으로 연결된 workflow (예: WB010, WB030)
- **Parallel UO**: 동일 시점에 여러 조건/replicate로 수행되는 UO

#### 검토 대상
- 이전 UO의 **Output**과 현재 UO의 **Input**이 일치하는가?
- 샘플 ID, 형식, 농도, 부피 등이 호환되는가?
- 중간 처리 단계(정제, 희석 등)가 누락되지 않았는가?

#### 표준 UO 코드 참조
LabNote Lite extension이 설치된 경우, extension의 unit operation 정의를 읽어와서 사용합니다.
- Extension 위치: `~/.vscode/extensions/` (또는 Windows: `%USERPROFILE%\.vscode\extensions\`)
- LabNote Lite extension 폴더: `kbiofoundry.labnote-lite-*`

표준 UO 코드 예시:
- **UH400**: Manual (수동 일반 작업)
- **UH010**: Liquid Handling (수동 액체 처리)
- **UHW010**: Liquid Handling - Workstation (자동화 액체 처리)
- **UHW100**: Thermocycling (PCR, incubation 등)
- **UHW180**: Incubation
- **UHW200**: Centrifugation
- **UHW230**: Nucleic Acid Fragment Analysis
- **UHW255**: Microplate Centrifugation
- **UHW130**: Sealing
- **WB010**: DNA Oligomer Assembly Workflow
- **WB030**: DNA Assembly Workflow
- **WB120**: Transformation Workflow

#### 검증 규칙
- ✅ 샘플 ID 일치 (예: DNA-20260102-001)
- ✅ 물리적 양 충분 (Output 부피 ≥ Input 부피)
- ✅ 상태/형식 호환 (예: PCR product → gel purification input)
- ✅ 농도/순도 요구사항 충족

#### 불일치 발견 시
```
UO1 Output: "Crude cell lysate, 10 mL"
UO2 Input: "Purified protein, 1 mg/mL"
→ ⚠️ 불일치: 중간 정제 단계 누락 가능성
```
사용자에게 확인 요청 및 누락된 UO 제안

### 5. Reference 대상 식별 (Unit Operation별)

#### 노트 유형 확인
- **Single UO**: 전체 노트에 대한 Reference 1회 처리
- **Multiple UO Workflow**: 각 UO별로 개별 Reference 처리

#### 각 Unit Operation별 Reference 대상
- 해당 UO의 Method 섹션에서 사용된 프로토콜, 절차, 파라미터
- 해당 UO의 Reagent/Equipment에 대한 사용법, 최적 조건
- 해당 UO의 Results & Discussions에서 언급된 이론적 배경
- 해당 UO의 실험 조건 (온도, 시간, 농도 등)

### 6. MCP 검색 수행 (Unit Operation별)

각 UO별로 개별 검색 수행:
- UO의 Description, Method, Results & Discussions에서 핵심 키워드 추출
- 해당 UO에 특화된 검색 쿼리 생성

검색 파라미터:
```
query: "{UO명} {핵심 키워드} protocol method conditions optimization"
type: "vector"
limit: 5-10 (UO당)
minimum_score: 0.3
search_notes: true
search_sources: true
```
검색 결과가 없으면 minimum_score를 0.2로 낮춰 재시도

검색 쿼리 예시:
- UHW010 Assembly PCR prep: "oligo pool concentration assembly PCR KOD One optimization"
- UHW100 Thermocycling: "assembly PCR cycling conditions temperature oligomer DNA"
- UHW180 Error-Correction: "T7 Endonuclease I mismatch heteroduplex correction"

### 7. Reference 섹션 분석 및 사용자 확인 (Unit Operation별)

#### 각 UO별로 순차적으로 처리
1. 첫 번째 UO의 Reference 검토
2. 사용자 확인 및 승인
3. 승인된 Reference 추가/수정
4. 다음 UO로 이동하여 반복

#### 각 UO의 기존 Reference 확인
- 해당 UO 섹션 마지막에 `#### Reference` 섹션이 있는지 확인
- 있는 경우: 기존 항목 목록 파악
- 없는 경우: 새로 추가 필요
- **Workflow 전체 Reference**: 마지막에 통합 Reference가 있는 경우, 해당 UO 관련 항목 추출

#### Reference 품질 검증 (UO별)
- 각 Reference 항목이 해당 UO의 Method/Results와 관련 있는지 확인
- MCP 검색 결과와 일치하는지 확인
- 출처 정보가 정확한지 확인 (Notebook명 > Note/Source명)

#### 사용자 확인 요청 (UO별, 필수)
```
📋 [{UO코드} {UO명}] Reference 검토 결과:

현재 상태:
- 기존 Reference: {개수}개 (이 UO 관련)
- MCP 검색 결과: {개수}개의 관련 자료 발견

추천 작업:
✅ 추가 권장: {개수}개
  1. **{핵심 요약}** — 출처: {Notebook명} > {Note/Source명}
  2. ...

⚠️ 수정 권장: {개수}개
  - 기존: "{부정확한 내용}"
  - 수정: "{정확한 내용}" — 출처: {올바른 출처}

❌ 삭제 권장: {개수}개 (검증 불가능)
  - "{내용}" — 이유: MCP에서 확인 불가

이 Unit Operation의 Reference 섹션을 수정/추가하시겠습니까? (예/아니오/건너뛰기)
- '예': 위 내용대로 이 UO의 Reference 섹션 업데이트
- '아니오' 또는 '건너뛰기': 이 UO의 Reference 작업 건너뛰고 다음 UO로
- '일부만': 추가할 항목 번호 지정 (예: 1,3)
- '전체 건너뛰기': 나머지 모든 UO의 Reference 작업 중단
```

### 8. Reference 섹션 작성 (사용자 승인 후, Unit Operation별)

#### 위치
각 UO 섹션의 "Results & Discussions" 바로 다음에 `#### Reference` 추가

#### 형식
```markdown
#### Results & Discussions
- (결과 및 토론 내용)

#### Reference
- **{핵심 요약}** — 출처: {Notebook명} > {Note/Source명}
- **{핵심 요약}** — 출처: {Notebook명} > {Note/Source명}

---

### [다음 UO 코드] 다음 UO 이름
```

#### 예시
```markdown
### [UHW010 Liquid Handling] Assembly PCR reaction mixture preparation

#### Results & Discussions
- 총 2가지 oligo pool 농도 조건으로 준비하였다.

#### Reference
- **Oligo pool 농도 최적화: 2.5 fmol/μL에서 조립 효율 최고** — 출처: goldengate > DNA Oligomer Assembly protocols
- **KOD One PCR Master Mix 최적 조건: 98°C denaturation, 30 cycles** — 출처: Protocol-DB > KOD polymerase manual

---

### [UHW100 Thermocycling] Assembly PCR reaction
```

### 9. 노트 업데이트 및 최종 보고

- **각 UO별로 Reference 섹션 추가/수정** (사용자 승인 받은 항목만)
- 기존 내용은 변경하지 않음 (Patch 방식)
- **처리 완료 후 진행 상황 보고**:
```
✅ [{UO코드}] Reference 추가 완료: {개수}개 추가됨
⏭️ 다음 UO로 이동: [{다음UO코드}]
```

- **전체 작업 완료 후 최종 요약 제공**:
```
📊 Reference 작업 완료 요약:

처리된 Unit Operations: {총 개수}개
- ✅ Reference 추가/수정: {개수}개 UO
- ⏭️ 건너뛰기: {개수}개 UO

총 추가된 Reference:
- UO별 분포: {UO1명: N개, UO2명: M개, ...}
- 전체 합계: {총 개수}개

기타 검증 결과:
- 템플릿 형식: {적합/부적합}
- 이전 노트와의 차이점: {요약}
- UO 흐름 검증: {적합/부적합}
```

---

## MCP 도구 사용

### mcp_my-mcp-server_search
Open Notebook에서 관련 문서 검색
```
query: "{UO명} {핵심 키워드} protocol method"
type: "vector"
limit: 5-10
minimum_score: 0.3
search_notes: true
search_sources: true
```

### mcp_my-mcp-server_set_notebook_scope
검색 범위를 특정 노트북으로 제한

**원칙 1**: 노트 주제에 맞는 Scope 자동 설정
- 노트 검토 시작 시 `list_notebooks()`로 사용 가능한 노트북 확인
- 현재 노트의 주제/키워드와 노트북 이름의 유사도를 판단하여 관련 노트북만 scope 설정
- 예: WB010 DNA Oligomer Assembly → `["goldengate"]` scope 설정

**원칙 2**: 검색 결과 부족 시 Scope 해제
- Scope 설정 후 검색 결과가 없거나 minimum_score 이하만 나올 경우
- `set_notebook_scope(notebooks=[])`로 scope 해제하고 전체 노트북에서 재검색
- 작업 완료 후 반드시 scope 해제하여 다음 노트 검토에 영향 없도록 함

---

## 제약 사항

- **MCP에서 제공하는 자료만 사용**: 추측하거나 외부 지식 사용 금지
- **검색 실패 시**: "검색 결과 없음. TODO: 수동 확인 필요" 명시
- **중복 방지**: 각 UO의 기존 Reference와 중복되지 않도록 추가
- **UO별 관련성 확인**: 각 Reference가 해당 UO와 직접 관련 있는지 확인
- **사용자 확인 필수**: 
  - 템플릿 누락 항목 발견 시
  - 이전 노트와의 불일치 발견 시
  - **각 Unit Operation의 Reference 추가/수정/삭제 전 반드시 확인 및 승인 필요**
  - UO 흐름 불일치 발견 시

## 품질 규칙

### ✅ 해야 하는 것
- MCP 검색 결과만 사용
- Reference는 간결하고 핵심만 기술 (1-2줄)
- 출처 정보 명확히 표기 (Notebook > Note/Source)
- 검색 실패 시 솔직하게 TODO 표시

### ❌ 하지 말아야 하는 것
- MCP 검색 없이 추측으로 Reference 작성
- 사용자가 작성한 본문 내용 수정
- 검색 결과가 없는데 억지로 내용 생성
- Reference 섹션 외 다른 부분 변경

---

## 참고 자료

- [labnote_template.md](./labnote_template.md): 표준 템플릿 형식
- [example_workflow.md](./examples/example_workflow.md): Multiple UO Workflow 예시
- [example_reference.md](./examples/example_reference.md): Reference 작성 예시
