#!/usr/bin/env python3
"""
베타카로틴 데이터를 사용한 ML 시스템 테스트
"""

import pandas as pd
import numpy as np
from ml_core import MLModelTrainer

def test_beta_carotene_data():
    """베타카로틴 데이터로 ML 시스템 테스트"""
    
    print("🧬 베타카로틴 ML 시스템 테스트 시작")
    print("=" * 50)
    
    # 1. 데이터 로드
    try:
        df = pd.read_excel('beta-carotene titer.xlsx')
        print(f"✅ 데이터 로드 성공: {df.shape[0]}행, {df.shape[1]}열")
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return
    
    # 2. 데이터 확인
    print("\n📊 데이터 구조:")
    print(f"컬럼: {list(df.columns)}")
    print(f"타겟 후보: avg (범위: {df['avg'].min():.3f} ~ {df['avg'].max():.3f})")
    print(f"특성 후보: CrtYB, CrtI, CrtE (각각 {df['CrtYB'].nunique()}, {df['CrtI'].nunique()}, {df['CrtE'].nunique()}개 카테고리)")
    
    # 3. 사용자 선택 시뮬레이션
    target_column = 'avg'
    selected_features = ['CrtYB', 'CrtI', 'CrtE']
    
    print(f"\n🎯 선택된 설정:")
    print(f"타겟 변수: {target_column}")
    print(f"특성 변수: {selected_features}")
    
    # 4. ML 모델 학습
    print(f"\n🤖 ML 모델 학습 시작...")
    
    trainer = MLModelTrainer()
    
    try:
        # 데이터 전처리
        X, y = trainer.preprocess_data(df, target_column, selected_features)
        print(f"✅ 전처리 완료: X shape = {X.shape}, y shape = {y.shape}")
        
        # 모델 학습
        results = trainer.train_models(X, y)
        print(f"✅ 모델 학습 완료")
        
        # 최고 성능 모델 정보
        print(f"\n🏆 최고 성능 모델:")
        print(f"모델: {trainer.best_model_name}")
        print(f"R² Score: {trainer.best_score:.4f}")
        
        # 모든 모델 성능
        print(f"\n📈 전체 모델 성능:")
        for model_name, score in results.items():
            print(f"  • {model_name}: {score:.4f}")
        
    except Exception as e:
        print(f"❌ ML 학습 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. 예측 테스트
    print(f"\n🔮 예측 테스트:")
    
    # 테스트 조건들
    test_conditions = [
        {'CrtYB': '(P) TDH3', 'CrtI': '(P) PGK1', 'CrtE': '(P) HHF1'},
        {'CrtYB': '(P) PGK1', 'CrtI': '(P) HHF1', 'CrtE': '(P) ALD6'},
        {'CrtYB': '(P) HHF1', 'CrtI': '(P) ALD6', 'CrtE': '(P) RNR1'},
    ]
    
    for i, condition in enumerate(test_conditions, 1):
        try:
            # 예측을 위한 데이터 준비
            test_df = pd.DataFrame([condition])
            
            # 누락된 특성 추가
            for feature in trainer.feature_names:
                if feature not in test_df.columns:
                    test_df[feature] = 0
            
            # 특성 순서 맞춤
            test_df = test_df[trainer.feature_names]
            
            # 인코딩
            X_encoded = test_df.copy()
            for column in X_encoded.columns:
                if column in trainer.label_encoders:
                    le = trainer.label_encoders[column]
                    if X_encoded[column].iloc[0] in le.classes_:
                        X_encoded[column] = le.transform(X_encoded[column])
                    else:
                        X_encoded[column] = 0
            
            # 스케일링
            X_scaled = trainer.scaler.transform(X_encoded)
            
            # 예측
            prediction = trainer.best_model.predict(X_scaled)[0]
            
            print(f"  {i}. {condition} → {prediction:.3f} mg/L")
            
        except Exception as e:
            print(f"  {i}. {condition} → 예측 오류: {e}")
    
    # 6. 베이지안 최적화 시뮬레이션
    print(f"\n🎯 베이지안 최적화 시뮬레이션:")
    
    try:
        from ml_core import BayesianOptimizer
        
        # 옵티마이저 설정
        optimizer = BayesianOptimizer(trainer)
        
        # 범위 설정 (범주형 변수만)
        categorical_dict = {}
        for feature in selected_features:
            categorical_dict[feature] = df[feature].unique().tolist()
        
        optimizer.set_categorical_features(categorical_dict)
        
        # 실험 조건 제안
        suggestions = optimizer.suggest_experiments(5)
        
        print(f"✅ 추천 실험 조건 ({len(suggestions)}개):")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
            
    except Exception as e:
        print(f"❌ 베이지안 최적화 오류: {e}")
    
    print(f"\n🎉 테스트 완료!")
    print("=" * 50)

if __name__ == "__main__":
    test_beta_carotene_data()