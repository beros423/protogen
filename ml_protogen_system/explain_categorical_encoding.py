import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import cross_val_score

def demonstrate_categorical_encoding():
    """범주형 데이터 인코딩 방법들의 차이 설명"""
    
    print("=== 범주형 데이터 인코딩 방법 비교 ===")
    print()
    
    # 베타카로틴 데이터와 유사한 예시 데이터 생성
    np.random.seed(42)
    
    # 범주형 데이터 (promoter)
    promoters = ['TDH3', 'PGK1', 'HHF1', 'ALD6', 'RNR1', 'RNR2']
    n_samples = 120
    
    # 예시 데이터 생성
    data = []
    for i in range(n_samples):
        crtYB = np.random.choice(promoters)
        crtI = np.random.choice(promoters)
        crtE = np.random.choice(promoters)
        
        # 실제 성능은 특정 조합에서만 높음 (실제 생물학적 관계 모방)
        if crtYB == 'TDH3' and crtI == 'PGK1':
            titer = 8 + np.random.normal(0, 1)
        elif crtE == 'TDH3':
            titer = 5 + np.random.normal(0, 1.5)
        else:
            titer = 2 + np.random.normal(0, 2)
        
        data.append([crtYB, crtI, crtE, max(0, titer)])
    
    df = pd.DataFrame(data, columns=['CrtYB', 'CrtI', 'CrtE', 'titer'])
    
    print(f"생성된 데이터 크기: {df.shape}")
    print(f"CrtYB 유니크 값: {df['CrtYB'].unique()}")
    print(f"타겟 통계: 평균={df['titer'].mean():.2f}, 표준편차={df['titer'].std():.2f}")
    print()
    
    # 1. Label Encoding (현재 방식)
    print("🏷️ 방법 1: Label Encoding (현재 방식)")
    print("  - 범주를 0,1,2,3,... 숫자로 변환")
    print("  - 문제: TDH3=0, PGK1=1이면 TDH3 < PGK1 같은 순서 관계 암시")
    
    df_label = df.copy()
    label_encoders = {}
    X_label = df_label[['CrtYB', 'CrtI', 'CrtE']].copy()
    
    for col in X_label.columns:
        label_encoders[col] = LabelEncoder()
        X_label[col] = label_encoders[col].fit_transform(X_label[col])
    
    model_label = LinearRegression()
    r2_label = cross_val_score(model_label, X_label, df['titer'], cv=5, scoring='r2').mean()
    
    print(f"  인코딩 예시: {dict(zip(promoters, range(len(promoters))))}")
    print(f"  R² 점수: {r2_label:.4f}")
    print()
    
    # 2. One-Hot Encoding (권장 방식)
    print("🔥 방법 2: One-Hot Encoding (권장 방식)")
    print("  - 각 범주를 별도의 0/1 컬럼으로 변환")
    print("  - 장점: 순서 관계 없음, 선형 모델에 적합")
    
    X_onehot = pd.get_dummies(df[['CrtYB', 'CrtI', 'CrtE']], prefix=['CrtYB', 'CrtI', 'CrtE'])
    
    model_onehot = LinearRegression()
    r2_onehot = cross_val_score(model_onehot, X_onehot, df['titer'], cv=5, scoring='r2').mean()
    
    print(f"  생성된 컬럼 수: {X_onehot.shape[1]}개")
    print(f"  컬럼 예시: {list(X_onehot.columns[:6])}...")
    print(f"  R² 점수: {r2_onehot:.4f}")
    print()
    
    # 3. 베타카로틴 데이터에 적용 해보기
    print("🧬 베타카로틴 데이터에 적용")
    try:
        beta_df = pd.read_excel('beta-carotene titer.xlsx')
        
        print("현재 Label Encoding 방식:")
        X_beta_label = beta_df[['CrtYB', 'CrtI', 'CrtE']].copy()
        label_enc = {}
        for col in X_beta_label.columns:
            label_enc[col] = LabelEncoder()
            X_beta_label[col] = label_enc[col].fit_transform(X_beta_label[col])
        
        model = LinearRegression()
        r2_beta_label = cross_val_score(model, X_beta_label, beta_df['avg'], cv=5, scoring='r2').mean()
        print(f"  Label Encoding R²: {r2_beta_label:.4f}")
        
        print("One-Hot Encoding 방식:")
        X_beta_onehot = pd.get_dummies(beta_df[['CrtYB', 'CrtI', 'CrtE']])
        r2_beta_onehot = cross_val_score(model, X_beta_onehot, beta_df['avg'], cv=5, scoring='r2').mean()
        print(f"  One-Hot Encoding R²: {r2_beta_onehot:.4f}")
        print(f"  생성된 특성 수: {X_beta_onehot.shape[1]}개")
        
        if r2_beta_onehot > r2_beta_label:
            print("  ✅ One-Hot Encoding이 더 좋은 성능!")
        else:
            print("  ⚠️ 현재 데이터에서는 큰 차이 없음")
            
    except FileNotFoundError:
        print("  (베타카로틴 파일을 찾을 수 없음)")
    
    print()
    print("📊 인코딩 방법 비교:")
    print("┌─────────────────┬──────────────┬──────────────┬─────────────┐")
    print("│    인코딩 방법    │   특성 개수   │   순서 관계   │   권장 용도  │")
    print("├─────────────────┼──────────────┼──────────────┼─────────────┤")
    print("│ Label Encoding  │     적음     │     있음     │ 트리 모델   │")
    print("│ One-Hot Encoding│     많음     │     없음     │ 선형 모델   │")
    print("└─────────────────┴──────────────┴──────────────┴─────────────┘")
    print()
    
    print("💡 베타카로틴 데이터에서는:")
    print("  - Promoter들 간에는 순서 관계가 없음")
    print("  - TDH3 > PGK1 같은 관계는 의미 없음")
    print("  - One-Hot Encoding이 생물학적으로 더 적합")
    print("  - 각 promoter의 독립적인 효과를 측정 가능")

if __name__ == "__main__":
    demonstrate_categorical_encoding()