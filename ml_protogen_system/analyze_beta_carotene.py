import pandas as pd

# 베타카로틴 데이터 로드
df = pd.read_excel('beta-carotene titer.xlsx')

print("=== 베타카로틴 데이터 분석 ===")
print(f"데이터 크기: {df.shape[0]}행, {df.shape[1]}열")

print("\n=== 컬럼 정보 ===")
for col in df.columns:
    print(f"• {col}: {df[col].nunique()}개 고유값, 타입: {df[col].dtype}")

print("\n=== 결측값 확인 ===")
missing = df.isnull().sum()
if missing.sum() > 0:
    print(missing[missing > 0])
else:
    print("결측값 없음")

print("\n=== 각 컬럼의 고유값 예시 ===")
for col in ['CrtYB', 'CrtI', 'CrtE']:
    unique_vals = df[col].unique()
    print(f"{col}: {list(unique_vals[:5])}{'...' if len(unique_vals) > 5 else ''}")

print("\n=== 타겟 후보 (수치형 컬럼) ===")
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
for col in numeric_cols:
    if col != 'Unnamed: 0':
        print(f"• {col}: 범위 {df[col].min():.3f} ~ {df[col].max():.3f}")

print("\n=== 특성 후보 (범주형 컬럼) ===")
categorical_cols = df.select_dtypes(include=['object']).columns
for col in categorical_cols:
    print(f"• {col}: {df[col].nunique()}개 카테고리")
    print(f"  예시: {list(df[col].unique()[:3])}")

print("\n=== ML 학습 제안 ===")
print("🎯 추천 타겟: 'avg' (평균 베타카로틴 농도)")
print("🎛️ 추천 특성: ['CrtYB', 'CrtI', 'CrtE'] (유전자 조합)")
print("❌ 제외 추천: ['Unnamed: 0', 'Unnamed: 4', 'n=1', 'n=2', 'n=3'] (식별자/개별 측정값)")