import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import pandas as pd

def demonstrate_negative_r2():
    """R² 값이 음수가 되는 경우를 시각적으로 설명"""
    
    print("=== R² 값이 음수가 되는 이유 설명 ===")
    print()
    
    # 1. 간단한 예시 데이터 생성
    np.random.seed(42)
    X = np.array([[1], [2], [3], [4], [5]])
    y_true = np.array([10, 8, 12, 9, 11])  # 실제값
    
    print("🔢 예시 데이터:")
    print(f"X: {X.flatten()}")
    print(f"y_true: {y_true}")
    print(f"y_true 평균: {np.mean(y_true):.2f}")
    print()
    
    # 2. 좋은 모델 (양의 R²)
    print("✅ 경우 1: 좋은 모델 (양의 R²)")
    y_pred_good = np.array([10.1, 8.2, 11.8, 9.1, 10.9])  # 좋은 예측
    
    # R² 계산 과정 보여주기
    y_mean = np.mean(y_true)
    sse_good = np.sum((y_true - y_pred_good)**2)
    sst = np.sum((y_true - y_mean)**2)
    r2_good = 1 - (sse_good / sst)
    
    print(f"  평균 예측 오차 (SST): {sst:.2f}")
    print(f"  모델 예측 오차 (SSE): {sse_good:.2f}")
    print(f"  R² = 1 - ({sse_good:.2f} / {sst:.2f}) = {r2_good:.4f}")
    print(f"  sklearn R²: {r2_score(y_true, y_pred_good):.4f}")
    print()
    
    # 3. 나쁜 모델 (음의 R²)
    print("❌ 경우 2: 나쁜 모델 (음의 R²)")
    y_pred_bad = np.array([5, 15, 3, 18, 2])  # 매우 나쁜 예측
    
    sse_bad = np.sum((y_true - y_pred_bad)**2)
    r2_bad = 1 - (sse_bad / sst)
    
    print(f"  평균 예측 오차 (SST): {sst:.2f}")
    print(f"  모델 예측 오차 (SSE): {sse_bad:.2f}")
    print(f"  R² = 1 - ({sse_bad:.2f} / {sst:.2f}) = {r2_bad:.4f}")
    print(f"  sklearn R²: {r2_score(y_true, y_pred_bad):.4f}")
    print()
    
    # 4. 베타카로틴 데이터에서의 실제 예
    print("🧬 베타카로틴 데이터에서 왜 음수인가?")
    
    # 베타카로틴 데이터 로드
    try:
        df = pd.read_excel('beta-carotene titer.xlsx')
        y = df['avg'].values
        y_mean = np.mean(y)
        
        print(f"  실제 타겟 범위: {np.min(y):.3f} ~ {np.max(y):.3f}")
        print(f"  실제 타겟 평균: {y_mean:.3f}")
        print(f"  실제 타겟 표준편차: {np.std(y):.3f}")
        
        # 문제가 있는 예측 예시 (과적합/잘못된 패턴 학습)
        # 모델이 학습한 패턴이 실제와 맞지 않아서 엉뚱한 예측을 하는 경우
        
        print()
        print("💡 베타카로틴 데이터에서 음수 R²가 나오는 이유:")
        print("  1. 📊 데이터 부족: 120개 샘플로 복잡한 패턴 학습 어려움")
        print("  2. 🔀 높은 노이즈: 실험 변동성(CV > 50%)이 신호를 가림")
        print("  3. 🎯 약한 신호: 특성과 타겟 간의 실제 관계가 미약함")
        print("  4. 🧮 과적합: 모델이 노이즈를 패턴으로 잘못 학습")
        print("  5. ❌ 잘못된 가정: 선형 관계가 아닐 수 있음")
        
    except FileNotFoundError:
        print("  (베타카로틴 파일을 찾을 수 없어 일반적인 설명만 제공)")
    
    print()
    print("🔍 R² 해석 가이드:")
    print("  R² > 0.7  : 🟢 매우 좋음")
    print("  R² 0.3-0.7: 🟡 보통")
    print("  R² 0-0.3  : 🟠 나쁨")
    print("  R² < 0    : 🔴 평균보다 못함 (랜덤 추측만도 못함)")
    print()
    
    print("⚡ 음수 R²일 때 해결 방법:")
    print("  1. 더 많은 양질의 데이터 수집")
    print("  2. 특성 엔지니어링 (새로운 변수 생성)")
    print("  3. 이상값 제거 및 데이터 정제")
    print("  4. 더 단순한 모델 사용")
    print("  5. 타겟 변수 변환 (로그, 제곱근 등)")

if __name__ == "__main__":
    demonstrate_negative_r2()