# 베타카로틴 생산 최적화 ML 시스템

이 프로젝트는 베타카로틴 생산을 최적화하기 위한 기계학습 기반 단백질 발현 시스템입니다.

## 핵심 기능

### ML 모델링
- **선형 모델 중심**: Ridge, Lasso, ElasticNet, Polynomial Regression
- **범주형 데이터**: One-Hot Encoding으로 Promoter 독립 효과 분석
- **타겟 변수 변환**: Log 변환으로 왜도 개선 및 성능 향상
- **자동 특성 선택**: Lasso/ElasticNet으로 중요 특성 자동 발견

### 데이터 처리
- **자동 전처리**: 결측값 처리, 스케일링, 인코딩 자동화
- **성능 진단**: 데이터 품질 이슈 자동 감지 및 개선 제안
- **실시간 디버깅**: 학습 과정 상세 로그 및 분석

### 실험 설계
- **베이지안 최적화**: 다음 실험 조건 자동 추천
- **매핑 파일 생성**: OT-2 로봇 실험용 파일 자동 생성
- **결과 추적**: 실험 결과 누적 학습 및 모델 개선

## 기술 스택
- **Frontend**: Streamlit 웹 애플리케이션
- **ML/AI**: scikit-learn, bayesian-optimization
- **Data**: pandas, numpy
- **Visualization**: plotly, matplotlib

## 생물학적 최적화
- Promoter 조합 효과 분석 (CrtYB, CrtI, CrtE)
- Beta-carotene titer 예측 및 최적화
- 실험 효율성 극대화