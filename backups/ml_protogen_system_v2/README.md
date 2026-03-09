# 베타카로틴 생산 최적화 ML 시스템 v2.0

🧬 **베타카로틴 생산을 위한 기계학습 기반 단백질 발현 시스템**

## 🎯 시스템 개요

이 시스템은 베타카로틴(Beta-carotene) 생산 최적화를 위한 **기계학습 기반 실험 설계 및 예측 시스템**입니다. Promoter 조합의 효과를 분석하고 최적 조건을 예측하여 실험 효율성을 극대화합니다.

## ✨ 주요 특징

### 🤖 **ML 모델링**
- **선형 모델 중심**: Ridge, Lasso, ElasticNet, Polynomial Regression
- **범주형 데이터**: One-Hot Encoding으로 Promoter 독립 효과 분석
- **타겟 변수 변환**: Log 변환으로 왜도 개선 및 성능 향상
- **자동 특성 선택**: Lasso/ElasticNet으로 중요 특성 자동 발견

### 📊 **데이터 처리**
- **자동 전처리**: 결측값 처리, 스케일링, 인코딩 자동화
- **성능 진단**: 데이터 품질 이슈 자동 감지 및 개선 제안
- **실시간 디버깅**: 학습 과정 상세 로그 및 분석

### 🧪 **실험 설계**
- **베이지안 최적화**: 다음 실험 조건 자동 추천
- **매핑 파일 생성**: OT-2 로봇 실험용 파일 자동 생성
- **결과 추적**: 실험 결과 누적 학습 및 모델 개선

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/username/ml_protogen_system_v2.git
cd ml_protogen_system_v2

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -e .
```

### 2. 실행

```bash
# Streamlit 앱 시작
streamlit run app.py
```

### 3. 데이터 준비

시스템에서 사용할 데이터는 다음 형식을 따라야 합니다:

| CrtYB | CrtI | CrtE | avg |
|-------|------|------|-----|
| (P) TDH3 | (P) PGK1 | (P) HHF1 | 15.2 |
| (P) ALD6 | (P) RNR1 | (P) TDH3 | 22.8 |
| ... | ... | ... | ... |

- **CrtYB, CrtI, CrtE**: Promoter 정보 (범주형)
- **avg**: 베타카로틴 titer (수치형, 타겟 변수)

## 📁 프로젝트 구조

```
ml_protogen_system_v2/
├── app.py                          # Streamlit 웹 애플리케이션
├── src/
│   └── ml_core.py                  # ML 핵심 기능
├── data/                           # 데이터 파일
├── models/                         # 학습된 모델 저장
├── tests/                          # 단위 테스트
├── requirements.txt                # Python 의존성
├── pyproject.toml                  # 프로젝트 설정
├── .github/
│   └── copilot-instructions.md     # AI 코딩 어시스턴트 가이드
└── README.md                       # 프로젝트 문서
```

## 🔬 기술 스택

### **Core ML/AI**
- **scikit-learn**: 기계학습 모델 및 전처리
- **bayesian-optimization**: 실험 조건 최적화
- **pandas & numpy**: 데이터 처리 및 수치 연산

### **Web Interface**
- **Streamlit**: 인터랙티브 웹 애플리케이션
- **plotly**: 동적 차트 및 시각화

### **Development**
- **pytest**: 단위 테스트 프레임워크
- **black & isort**: 코드 포맷팅
- **mypy**: 정적 타입 검사

## 📊 성능 향상 기법

### 1. **범주형 데이터 처리**
```python
# 기존: Label Encoding (순서 관계 가정)
CrtYB: TDH3=0, PGK1=1, HHF1=2  # 부적절

# 개선: One-Hot Encoding (독립적 효과)
CrtYB_TDH3: 1, CrtYB_PGK1: 0, CrtYB_HHF1: 0  # 적절
```

### 2. **타겟 변수 변환**
```python
# 베타카로틴 데이터는 일반적으로 오른쪽 치우침
# Log 변환으로 정규분포화 → 성능 향상
y_transformed = log(y + 1)  # +1로 0값 처리
```

### 3. **모델 선택 전략**
- **소규모 데이터**: 선형 모델 (Ridge, Lasso) 우선
- **과적합 방지**: 교차 검증 + 정규화
- **해석 가능성**: 계수 분석으로 Promoter 효과 이해

## 📈 성능 벤치마크

| 개선 항목 | 이전 R² | 개선 후 R² | 향상폭 |
|-----------|---------|------------|--------|
| 범주형 인코딩 | -0.39 | +0.15 | +0.54 |
| 타겟 변환 | +0.15 | +0.35 | +0.20 |
| 정규화 적용 | +0.35 | +0.42 | +0.07 |

## 🧪 사용 예시

### 1. **기본 학습**
```python
from src.ml_core import MLModelTrainer

trainer = MLModelTrainer(
    model_preference='linear_focused',
    encoding_method='auto',  # One-Hot 우선
    target_transform='auto'  # Log 변환 자동
)

X, y = trainer.preprocess_data(df, 'avg', ['CrtYB', 'CrtI', 'CrtE'])
results = trainer.train_models(X, y)
```

### 2. **고급 설정**
```python
trainer = MLModelTrainer(
    model_preference='all',
    encoding_method='onehot_drop',
    target_transform='log',
    cv_folds=5,
    random_state=42
)
```

## 🔧 설정 가이드

### **데이터 품질 요구사항**
- **최소 샘플 수**: 50개 이상 권장
- **결측값**: 20% 이하
- **타겟 분포**: 왜도 < 2.0 또는 Log 변환 적용

### **모델 선택 기준**
- **R² > 0.7**: 실용적 예측 성능
- **R² 0.3-0.7**: 트렌드 분석 가능
- **R² < 0.3**: 데이터 품질 또는 모델 개선 필요

## 🧬 생물학적 해석

### **Promoter 효과 분석**
- **CrtYB**: Beta-carotene synthase 발현 조절
- **CrtI**: Phytoene desaturase 발현 조절  
- **CrtE**: Geranylgeranyl diphosphate synthase 발현 조절

### **최적화 목표**
- **주요 목표**: Beta-carotene titer 최대화
- **제약 조건**: 세포 성장 유지, 대사 균형
- **실험 효율**: 베이지안 최적화로 실험 횟수 최소화

## 🤝 기여하기

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/새기능`)
3. 변경사항 커밋 (`git commit -am '새 기능 추가'`)
4. 브랜치에 푸시 (`git push origin feature/새기능`)
5. Pull Request 생성

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의

- **이슈 리포트**: [GitHub Issues](https://github.com/username/ml_protogen_system_v2/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/username/ml_protogen_system_v2/discussions)

---

**🧬 베타카로틴 생산 최적화의 새로운 패러다임을 경험해보세요!**