import pandas as pd
import numpy as np
from datetime import datetime


def generate_test_experiment_results(mapping_df: pd.DataFrame, target_column: str = "Expression_Level") -> pd.DataFrame:
    """
    매핑 파일을 기반으로 테스트용 실험 결과 데이터 생성
    
    Args:
        mapping_df: 매핑 파일 DataFrame
        target_column: 타겟 변수명 (기본값: "Expression_Level")
    
    Returns:
        실험 결과가 포함된 DataFrame
    """
    results_df = mapping_df.copy()
    
    # 실험 조건에 기반한 가상의 결과 생성
    np.random.seed(42)  # 재현 가능한 결과를 위해
    
    n_samples = len(results_df)
    
    # 기본 성능값 (100-200 범위)
    base_performance = np.random.normal(150, 20, n_samples)
    
    # 각 변수에 따른 효과 추가
    for col in results_df.columns:
        if col in ['Well', 'Sample_ID', target_column]:
            continue
            
        if results_df[col].dtype == 'object':  # 범주형 변수
            unique_vals = results_df[col].unique()
            # 각 범주에 다른 효과 부여
            effects = {}
            for i, val in enumerate(unique_vals):
                effects[val] = np.random.normal(0, 15)  # -15 ~ +15 범위의 효과
            
            for val, effect in effects.items():
                mask = results_df[col] == val
                base_performance[mask] += effect
                
        elif pd.api.types.is_numeric_dtype(results_df[col]):  # 수치형 변수
            # 수치형 변수는 비선형 관계 생성
            normalized_val = (results_df[col] - results_df[col].mean()) / results_df[col].std()
            
            # 2차 함수 형태의 효과 (최적점이 있는 형태)
            effect = 20 * (1 - normalized_val**2) + np.random.normal(0, 5, n_samples)
            base_performance += effect
    
    # 노이즈 추가
    noise = np.random.normal(0, 10, n_samples)
    base_performance += noise
    
    # 음수값 방지
    base_performance = np.maximum(base_performance, 10)
    
    # 소수점 1자리로 반올림
    results_df[target_column] = np.round(base_performance, 1)
    
    return results_df


def create_sample_mapping_for_testing():
    """테스트용 샘플 매핑 데이터 생성"""
    
    # 샘플 실험 조건들
    experiments = []
    
    promoters = ['P1', 'P2', 'P3']
    genes = ['Gene_A', 'Gene_B', 'Gene_C']
    temperatures = [28.0, 30.0, 32.0, 34.0]
    ph_values = [6.8, 7.0, 7.2, 7.4]
    concentrations = [0.2, 0.5, 0.8]
    
    # 다양한 조합 생성 (15개 실험)
    counter = 0
    for promoter in promoters:
        for gene in genes[:2]:  # 처음 2개 유전자만
            if counter >= 15:
                break
            
            experiment = {
                'Promoter': promoter,
                'CDS': gene,
                'Temperature': np.random.choice(temperatures),
                'pH': np.random.choice(ph_values),
                'Inducer_Conc': np.random.choice(concentrations)
            }
            experiments.append(experiment)
            counter += 1
    
    # 웰 포지션 생성
    well_positions = []
    for row in range(3):  # A, B, C 행
        for col in range(5):  # 1-5 열
            row_letter = chr(ord('A') + row)
            well_positions.append(f"{row_letter}{col+1:02d}")
    
    # 매핑 DataFrame 생성
    mapping_data = []
    for i, experiment in enumerate(experiments):
        mapping_row = {
            'Well': well_positions[i],
            'Sample_ID': f"Sample_{i+1:03d}",
            **experiment
        }
        mapping_data.append(mapping_row)
    
    return pd.DataFrame(mapping_data)


def save_test_results_template(mapping_df: pd.DataFrame, target_column: str = "Expression_Level", 
                             filename: str = "test_experiment_results.csv"):
    """테스트 결과 템플릿 파일 생성 및 저장"""
    
    results_df = generate_test_experiment_results(mapping_df, target_column)
    results_df.to_csv(filename, index=False)
    
    print(f"테스트 결과 파일이 생성되었습니다: {filename}")
    print(f"샘플 수: {len(results_df)}")
    print(f"컬럼: {list(results_df.columns)}")
    print("\n결과 미리보기:")
    print(results_df.head())
    
    return results_df


if __name__ == "__main__":
    # 테스트 실행
    print("테스트용 매핑 데이터 생성...")
    sample_mapping = create_sample_mapping_for_testing()
    
    print("\n매핑 데이터:")
    print(sample_mapping)
    
    print("\n테스트 결과 생성...")
    test_results = save_test_results_template(sample_mapping)
    
    # 통계 정보 출력
    target_col = "Expression_Level"
    print(f"\n{target_col} 통계:")
    print(f"평균: {test_results[target_col].mean():.2f}")
    print(f"표준편차: {test_results[target_col].std():.2f}")
    print(f"최소값: {test_results[target_col].min():.2f}")
    print(f"최대값: {test_results[target_col].max():.2f}")