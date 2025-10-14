"""
베타카로틴 생산 최적화 ML 시스템 기본 테스트
간단한 샘플 데이터로 시스템 기능을 검증합니다.
"""

import pandas as pd
import numpy as np
from src.ml_core import MLModelTrainer

def create_sample_data():
    """베타카로틴 실험 샘플 데이터 생성"""
    np.random.seed(42)
    
    promoters = ['(P) TDH3', '(P) PGK1', '(P) HHF1', '(P) ALD6', '(P) RNR1', '(P) RNR2']
    
    n_samples = 50
    data = []
    
    for i in range(n_samples):
        crtYB = np.random.choice(promoters)
        crtI = np.random.choice(promoters)
        crtE = np.random.choice(promoters)
        
        # Promoter 효과를 시뮬레이션
        base_titer = 10.0
        
        # 각 promoter의 강도 (실제 생물학적 데이터 기반 근사)
        strength_map = {
            '(P) TDH3': 1.5,
            '(P) PGK1': 1.2,
            '(P) HHF1': 1.0,
            '(P) ALD6': 0.8,
            '(P) RNR1': 0.6,
            '(P) RNR2': 0.4
        }
        
        # 상호작용 효과 포함
        titer = (base_titer * 
                strength_map[crtYB] * 
                strength_map[crtI] * 
                strength_map[crtE] + 
                np.random.normal(0, 2))  # 노이즈 추가
        
        titer = max(0.1, titer)  # 음수 방지
        
        data.append({
            'CrtYB': crtYB,
            'CrtI': crtI,
            'CrtE': crtE,
            'avg': titer
        })
    
    return pd.DataFrame(data)

def test_system():
    """시스템 기능 종합 테스트"""
    print("🧬 베타카로틴 생산 최적화 ML 시스템 테스트 시작")
    print("=" * 50)
    
    # 1. 샘플 데이터 생성
    print("📊 샘플 데이터 생성 중...")
    df = create_sample_data()
    print(f"✅ 샘플 데이터 생성 완료: {df.shape}")
    print(f"   - 특성: {list(df.columns[:-1])}")
    print(f"   - 타겟: {df.columns[-1]}")
    print(f"   - 베타카로틴 평균: {df['avg'].mean():.2f}")
    print()
    
    # 2. MLModelTrainer 초기화
    print("🤖 ML 모델 트레이너 초기화 중...")
    trainer = MLModelTrainer(
        model_preference='linear_focused',
        encoding_method='auto',
        target_transform='auto'
    )
    print("✅ ML 모델 트레이너 초기화 완료")
    print()
    
    # 3. 데이터 전처리
    print("📈 데이터 전처리 중...")
    feature_columns = ['CrtYB', 'CrtI', 'CrtE']
    target_column = 'avg'
    
    X, y = trainer.preprocess_data(df, target_column, feature_columns)
    print(f"✅ 전처리 완료: X={X.shape}, y={y.shape}")
    print()
    
    # 4. 모델 학습
    print("🎯 모델 학습 중...")
    results = trainer.train_models(X, y)
    print("✅ 모델 학습 완료")
    print()
    
    # 5. 결과 분석
    print("📊 학습 결과 분석:")
    print("-" * 30)
    
    valid_results = {k: v for k, v in results.items() if isinstance(v, (int, float)) and v > -100}
    
    if valid_results:
        best_model = max(valid_results, key=valid_results.get)
        best_score = valid_results[best_model]
        
        print(f"🏆 최고 성능 모델: {best_model}")
        print(f"📈 최고 R² 점수: {best_score:.4f}")
        
        # 성능 해석
        if best_score < 0:
            performance = "🚨 성능이 베이스라인보다 낮음"
        elif best_score < 0.3:
            performance = "⚠️ 성능 개선 필요"
        elif best_score < 0.7:
            performance = "📊 보통 수준 성능"
        else:
            performance = "🎉 우수한 성능"
        
        print(f"💡 성능 평가: {performance}")
        
        print("\n📋 전체 모델 성능:")
        for model, score in sorted(valid_results.items(), key=lambda x: x[1], reverse=True):
            print(f"   {model:15s}: {score:8.4f}")
        
    else:
        print("❌ 유효한 학습 결과가 없습니다.")
    
    print("\n" + "=" * 50)
    print("🎉 베타카로틴 생산 최적화 ML 시스템 테스트 완료!")
    
    return trainer, results

if __name__ == "__main__":
    trainer, results = test_system()