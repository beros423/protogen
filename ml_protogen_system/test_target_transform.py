import pandas as pd
import numpy as np
from ml_core import MLModelTrainer

def test_target_transformation():
    """타겟 변수 변환 효과 테스트"""
    
    print("=== 타겟 변수 변환 효과 테스트 ===")
    
    # 데이터 로드
    df = pd.read_excel('beta-carotene titer.xlsx')
    feature_columns = ['CrtYB', 'CrtI', 'CrtE']
    target_column = 'avg'
    
    print(f"베타카로틴 데이터: {df.shape}")
    
    # 타겟 변수 분포 분석
    y = df[target_column]
    print(f"\n📊 원본 타겟 변수 분포:")
    print(f"  - 범위: {y.min():.3f} ~ {y.max():.3f}")
    print(f"  - 평균: {y.mean():.3f} ± {y.std():.3f}")
    print(f"  - 왜도: {y.skew():.3f}")
    print(f"  - 0값 개수: {(y == 0).sum()}/{len(y)} ({(y == 0).sum()/len(y)*100:.1f}%)")
    
    # 다양한 변환 방법 테스트
    transform_methods = ['none', 'log', 'sqrt', 'auto']
    results = {}
    
    for transform in transform_methods:
        print(f"\n🔄 {transform} 변환 테스트:")
        
        try:
            # Trainer 생성 (One-Hot 인코딩 + 타겟 변환)
            trainer = MLModelTrainer(
                model_preference='linear_focused',
                encoding_method='auto',  # 기본적으로 One-Hot 선호
                target_transform=transform
            )
            
            # 데이터 전처리 및 모델 학습
            X, y_transformed = trainer.preprocess_data(df, target_column, feature_columns)
            model_results = trainer.train_models(X, y_transformed)
            
            # 결과 저장
            results[transform] = {
                'best_model': trainer.best_model_name,
                'best_score': trainer.best_score,
                'is_transformed': trainer.is_target_transformed,
                'transformer': trainer.target_transformer,
                'model_results': model_results
            }
            
            print(f"✅ 완료: {trainer.best_model_name}, R²={trainer.best_score:.4f}")
            
        except Exception as e:
            print(f"❌ 오류: {str(e)}")
            results[transform] = {'error': str(e)}
    
    # 결과 비교
    print(f"\n🏆 타겟 변환 방법별 최종 비교:")
    print("=" * 80)
    print(f"{'변환 방법':<10} {'변환 적용':<10} {'최고 모델':<20} {'R² 점수':<12} {'개선도':<10}")
    print("=" * 80)
    
    best_transform = None
    best_score = float('-inf')
    baseline_score = results.get('none', {}).get('best_score', float('-inf'))
    
    for transform, result in results.items():
        if 'error' not in result:
            model_name = result['best_model'] or 'None'
            score = result['best_score']
            is_transformed = result['is_transformed']
            
            # 개선도 계산
            if baseline_score != float('-inf') and transform != 'none':
                improvement = score - baseline_score
                improvement_str = f"+{improvement:.4f}" if improvement > 0 else f"{improvement:.4f}"
            else:
                improvement_str = "기준"
            
            transform_status = "✅" if is_transformed else "❌"
            
            print(f"{transform:<10} {transform_status:<10} {model_name:<20} {score:<12.4f} {improvement_str:<10}")
            
            if score > best_score:
                best_score = score
                best_transform = transform
        else:
            print(f"{transform:<10} {'ERROR':<10} {'':<20} {'':<12} {'':<10}")
    
    print("=" * 80)
    
    if best_transform:
        print(f"\n🥇 최고 성능 변환: {best_transform}")
        print(f"   최고 R² 점수: {best_score:.4f}")
        
        if baseline_score != float('-inf'):
            improvement = best_score - baseline_score
            if improvement > 0:
                print(f"   📈 변환 없음 대비 개선: +{improvement:.4f}")
            else:
                print(f"   📉 변환 없음 대비 악화: {improvement:.4f}")
    
    # 변환 효과 분석
    print(f"\n💡 베타카로틴 데이터 변환 분석:")
    
    if best_score > baseline_score:
        print(f"✅ 타겟 변환이 성능 개선에 도움됨")
        print(f"   최적 변환: {best_transform}")
        
        best_result = results[best_transform]
        if best_result['transformer']:
            print(f"   적용된 변환: {best_result['transformer']}")
        
    else:
        print(f"❓ 타겟 변환이 큰 도움이 안 됨")
        print(f"   원인: 데이터 품질 문제가 더 근본적일 수 있음")
    
    # 베타카로틴 데이터 특성 분석
    print(f"\n🧬 베타카로틴 데이터 특성:")
    print(f"  - 0값 존재: {(y == 0).sum()}개 → Log 변환이 적합할 수 있음")
    print(f"  - 왜도 {y.skew():.3f}: {'높음' if abs(y.skew()) > 1 else '보통'} → 변환 필요성 {'높음' if abs(y.skew()) > 1 else '보통'}")
    print(f"  - 분산: {y.var():.3f} → Square Root 변환도 고려 가능")
    
    return results

if __name__ == "__main__":
    results = test_target_transformation()