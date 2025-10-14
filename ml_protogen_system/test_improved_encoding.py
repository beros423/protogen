import pandas as pd
import numpy as np
from ml_core import MLModelTrainer

def test_improved_categorical_encoding():
    """개선된 범주형 인코딩으로 베타카로틴 데이터 테스트"""
    
    print("=== 개선된 범주형 인코딩 테스트 ===")
    
    # 데이터 로드
    df = pd.read_excel('beta-carotene titer.xlsx')
    feature_columns = ['CrtYB', 'CrtI', 'CrtE']
    target_column = 'avg'
    
    print(f"데이터: {df.shape}, 범주형 특성: {feature_columns}")
    print(f"각 특성별 범주 수: {[df[col].nunique() for col in feature_columns]}")
    
    # 다양한 인코딩 방법 테스트
    encoding_methods = ['label', 'onehot_drop', 'auto']
    results = {}
    
    for encoding in encoding_methods:
        print(f"\n🔄 {encoding} 인코딩 테스트:")
        
        try:
            # Trainer 생성
            trainer = MLModelTrainer(
                model_preference='linear_focused', 
                encoding_method=encoding
            )
            
            # 데이터 전처리
            X, y = trainer.preprocess_data(df, target_column, feature_columns)
            
            # 모델 학습
            model_results = trainer.train_models(X, y)
            
            # 결과 저장
            results[encoding] = {
                'best_model': trainer.best_model_name,
                'best_score': trainer.best_score,
                'feature_count': X.shape[1],
                'model_results': model_results
            }
            
            print(f"✅ 완료: 최고 모델={trainer.best_model_name}, R²={trainer.best_score:.4f}, 특성수={X.shape[1]}")
            
        except Exception as e:
            print(f"❌ 오류: {str(e)}")
            results[encoding] = {'error': str(e)}
    
    # 결과 비교
    print(f"\n🏆 인코딩 방법별 최종 비교:")
    print("=" * 70)
    print(f"{'인코딩 방법':<15} {'최고 모델':<20} {'R² 점수':<12} {'특성 수':<10}")
    print("=" * 70)
    
    best_encoding = None
    best_score = float('-inf')
    
    for encoding, result in results.items():
        if 'error' not in result:
            model_name = result['best_model'] or 'None'
            score = result['best_score']
            feature_count = result['feature_count']
            
            print(f"{encoding:<15} {model_name:<20} {score:<12.4f} {feature_count:<10}")
            
            if score > best_score:
                best_score = score
                best_encoding = encoding
        else:
            print(f"{encoding:<15} {'ERROR':<20} {'':<12} {'':<10}")
    
    print("=" * 70)
    
    if best_encoding:
        print(f"\n🥇 최고 성능 인코딩: {best_encoding}")
        print(f"   최고 R² 점수: {best_score:.4f}")
        
        # 최고 성능 모델의 세부 정보
        best_result = results[best_encoding]
        print(f"\n📊 {best_encoding} 인코딩 세부 결과:")
        for model_name, score in best_result['model_results'].items():
            status = "🏆" if model_name == best_result['best_model'] else "  "
            print(f"  {status} {model_name}: {score:.4f}")
    
    # 베타카로틴 데이터에 대한 결론
    print(f"\n💡 베타카로틴 데이터 분석 결론:")
    
    if best_score < 0:
        print("❌ 모든 방법에서 음수 R² → 근본적인 데이터 품질 문제")
        print("   해결 방안:")
        print("   1. 특성 상호작용 추가 (CrtYB × CrtI × CrtE)")
        print("   2. 타겟 변수 변환 (log, sqrt)")
        print("   3. 이상값 제거 및 데이터 정제")
        print("   4. 더 많은 실험 데이터 (누락된 96개 조합)")
    elif best_score < 0.3:
        print("⚠️ 성능 개선 여지 있음")
        print(f"   {best_encoding} 인코딩이 상대적으로 우수함")
    else:
        print("✅ 합리적인 성능 달성")
    
    print(f"\n🧬 생물학적 관점에서의 권장사항:")
    print("   - Promoter는 명목형 데이터 → One-Hot 인코딩이 이론적으로 적합")
    print("   - Label 인코딩은 순서 관계를 잘못 가정할 수 있음")
    print("   - 하지만 소규모 데이터에서는 차원 저주 문제로 Label이 더 나을 수 있음")
    
    return results

if __name__ == "__main__":
    results = test_improved_categorical_encoding()