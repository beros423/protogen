import pandas as pd
import numpy as np
from ml_core import MLModelTrainer

def test_linear_focused_models():
    """선형 모델 중심으로 베타카로틴 데이터 테스트"""
    
    print("=== 선형 모델 중심 베타카로틴 데이터 테스트 ===")
    
    # 1. 데이터 로드
    file_path = r'beta-carotene titer.xlsx'
    df = pd.read_excel(file_path)
    
    print(f"데이터 크기: {df.shape}")
    print(f"특성: CrtYB, CrtI, CrtE")
    print(f"타겟: avg (beta-carotene titer)")
    
    # 2. 선형 모델 중심 trainer 생성
    trainer = MLModelTrainer(model_preference='linear_focused')
    
    print(f"\n사용할 모델들: {list(trainer.models.keys())}")
    
    # 3. 데이터 전처리
    feature_columns = ['CrtYB', 'CrtI', 'CrtE']
    target_column = 'avg'
    
    print(f"\n=== 데이터 전처리 ===")
    X, y = trainer.preprocess_data(df, target_column, feature_columns)
    
    # 4. 모델 학습 및 평가
    print(f"\n=== 선형 모델들 학습 및 평가 ===")
    results = trainer.train_models(X, y)
    
    # 5. 결과 요약
    print(f"\n=== 최종 결과 요약 ===")
    print(f"최고 성능 모델: {trainer.best_model_name}")
    print(f"최고 R² 점수: {trainer.best_score:.4f}")
    
    # 6. 선형 모델 계수 분석
    if (trainer.best_model_name and 
        any(model_type in trainer.best_model_name.lower() 
            for model_type in ['linear', 'ridge', 'lasso', 'elastic'])):
        
        print(f"\n=== 선형 모델 계수 분석 ===")
        if hasattr(trainer.best_model, 'coef_'):
            coefficients = trainer.best_model.coef_
            intercept = getattr(trainer.best_model, 'intercept_', 0)
            
            print(f"절편 (intercept): {intercept:.4f}")
            print("특성별 계수:")
            for i, (feature, coef) in enumerate(zip(trainer.feature_names, coefficients)):
                direction = "양의 영향 ↗️" if coef > 0 else "음의 영향 ↘️"
                print(f"  {feature}: {coef:.4f} ({direction})")
    
    # 7. 성능 개선 제안
    print(f"\n=== 성능 개선 제안 ===")
    data_size = len(y)
    feature_count = len(feature_columns)
    
    if trainer.best_score < 0:
        print("❌ 모델 성능이 베이스라인보다 낮음")
        print("제안:")
        print("1. 특성 엔지니어링: 상호작용 항 추가 (CrtYB × CrtI 등)")
        print("2. 타겟 변수 변환: log 변환 또는 Box-Cox 변환")
        print("3. 이상값 제거: 실험 오류로 보이는 데이터 점 확인")
        print("4. 더 많은 데이터: 누락된 96개 조합 실험")
    elif trainer.best_score < 0.3:
        print("⚠️ 성능 개선 필요")
        print("제안:")
        print("1. 정규화 강도 조정 (Ridge/Lasso alpha 값)")
        print("2. 다항 특성 추가 (2차 항)")
        print("3. 실험 반복성 개선")
    else:
        print("✅ 합리적인 성능")
    
    return results, trainer

if __name__ == "__main__":
    results, trainer = test_linear_focused_models()