# K-BioFoundry Labnote Writer - Agent Skills

이 프로젝트는 K-BioFoundry 연구노트 작성 및 관리를 돕는 Agent Skills 모음입니다.

## 📦 설치된 Skills

### 1. [labnote-review](./skills/labnote-review/SKILL.md)
연구노트를 검토하고 MCP 검색을 통해 Reference를 추가합니다.

**주요 기능:**
- 템플릿 형식 검증
- 이전/이후 노트와 일관성 확인
- Unit Operation 흐름 검토 (Input/Output 호환성)
- MCP 기반 Reference 추가

**사용 시점:**
- "노트 검토해줘"
- "reference 추가해줘"
- Workflow 내 UO 흐름 검증이 필요한 경우

---

### 2. [sample-tracking](./sample-tracking/SKILL.md)
로컬 labnotes 폴더를 검색하여 Sample ID의 출처, 사용 이력, 파생 샘플, 용량 등을 추적합니다.

**주요 기능:**
- 샘플 출처 (Source Tree) 추적
- 사용 이력 (Usage History) 정리
- 파생 샘플 (Derived Samples) 리스트
- 용량 추적 (Volume Tracking)
- 전체 타임라인 분석

**사용 시점:**
- "DNA-20250101-001 출처 알려줘"
- "이 샘플 얼마나 남았어?"
- "샘플 사용 이력 보여줘"

---

### 3. [experiment-statistics](./experiment-statistics/SKILL.md)
로컬 labnotes 폴더를 검색하여 특정 실험/프로토콜의 소요 시간 통계를 분석하고 예측합니다.

**주요 기능:**
- 평균/중앙값/범위 계산
- 최근 이력 추적
- 시간 분포 분석
- 실험 계획 지원

**사용 시점:**
- "Golden Gate 얼마나 걸려?"
- "PCR 평균 시간 알려줘"
- "Transformation 시간 통계"

---

## 🚀 Skills 활성화 방법

1. **VS Code 설정 확인**
   ```
   Settings > Chat: Use Agent Skills 활성화
   ```

2. **Skills 위치**
   - Project skills: `.github/skills/` (현재 프로젝트)
   - Personal skills: `~/.copilot/skills/` (전체 사용자)

3. **자동 로드**
   - Skills는 사용자 요청에 맞춰 자동으로 로드됩니다
   - 수동 선택 불필요 (Progressive Disclosure)

---

## 📂 Skills 구조

```
.github/skills/
├── labnote-review/
│   ├── SKILL.md                      # Skill 정의 (메타데이터 + 상세 지침)
│   ├── labnote_template.md           # 참조용 템플릿
│   └── examples/
│       ├── example_workflow.md       # Workflow 예시
│       └── example_reference.md      # Reference 작성 예시
├── sample-tracking/
│   ├── SKILL.md
│   └── examples/
│       └── tracking_examples.md      # 추적 시나리오 예시
└── experiment-statistics/
    ├── SKILL.md
    └── examples/
        └── statistics_examples.md    # 통계 분석 예시
```

---

## 🔧 데이터 소스

### labnote-review
Open Notebook MCP 서버와 연동하여 외부 참고 자료를 검색합니다.

**사용 MCP 도구:**

1. **mcp_my-mcp-server_search**
   - Open Notebook에서 관련 문서 검색
   - Vector search 기반 유사도 검색

2. **mcp_my-mcp-server_set_notebook_scope**
   - 검색 범위를 특정 노트북으로 제한
   - 주제에 맞는 Scope 자동 설정

3. **mcp_my-mcp-server_list_notebooks**
   - 사용 가능한 노트북 목록 조회

### sample-tracking & experiment-statistics
로컬 labnotes 폴더 (./labnotes)를 직접 검색합니다.

**사용 도구:**

1. **semantic_search**
   - 워크스페이스 내 코드/문서 의미론적 검색
   - Sample ID, 실험명으로 관련 노트 검색

2. **grep_search**
   - 텍스트 패턴 기반 빠른 검색
   - 정확한 Sample ID 매칭, 실험 유형 필터링

3. **read_file**
   - 노트 파일 내용 읽기
   - 시간 데이터, 용량 정보 추출

---

## 📖 사용 예시

### 노트 검토 및 Reference 추가
```
사용자: 20260102_002_goldengate_assembly.md 노트 검토해줘
AI: [labnote-review skill 자동 로드]
    1. 템플릿 형식 확인
    2. MCP 검색으로 관련 Reference 발견
    3. 사용자 확인 후 Reference 섹션 추가
```

### 샘플 추적
```
사용자: DNA-20260102-001 용량 알려줘
AI: [sample-tracking skill 자동 로드]
    1. 로컬 labnotes 폴더에서 제작/사용 노트 검색
    2. 용량 계산 및 사용 이력 정리
    3. 결과 출력
```

### 실험 시간 통계
```
사용자: PCR 평균 시간 알려줘
AI: [experiment-statistics skill 자동 로드]
    1. 로컬 labnotes 폴더에서 PCR 노트 검색
    2. 시간 데이터 추출 및 통계 계산
    3. 결과 및 권장 사항 제공
```

---

## ⚙️ Skills 커스터마이징

### 새로운 Skill 추가

1. `.github/skills/` 디렉토리에 새 폴더 생성
2. `SKILL.md` 파일 작성:
   ```markdown
   ---
   name: my-skill
   description: What the skill does and when to use it
   ---
   
   # Skill Instructions
   
   Your detailed instructions here...
   ```

3. 필요 시 예제/스크립트 추가
4. Copilot이 자동으로 인식

### 기존 Skill 수정

- `SKILL.md` 파일 직접 편집
- 예제 파일 추가/수정
- 변경사항 즉시 반영 (재시작 불필요)

---

## 📚 참고 자료

- [Agent Skills 공식 문서](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
- [Agent Skills 표준](https://agentskills.io/)
- [Skills 예시 저장소](https://github.com/anthropics/skills)
- [VS Code Copilot 커스터마이징](https://code.visualstudio.com/docs/copilot/customization/overview)

---

## 🤝 기여

Skills 개선 아이디어나 버그 리포트는 이슈로 등록해 주세요.

---

## 📄 라이센스

MIT License
