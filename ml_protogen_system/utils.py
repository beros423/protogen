import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Tuple


def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = None) -> bool:
    """데이터프레임 유효성 검사"""
    if df is None or df.empty:
        return False
    
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return False
    
    return True


def encode_categorical_features(df: pd.DataFrame, categorical_columns: List[str] = None) -> Tuple[pd.DataFrame, Dict]:
    """범주형 특성 인코딩"""
    df_encoded = df.copy()
    encoders = {}
    
    if categorical_columns is None:
        categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
    
    for col in categorical_columns:
        if col in df.columns:
            encoder = LabelEncoder()
            df_encoded[col] = encoder.fit_transform(df[col].astype(str))
            encoders[col] = encoder
    
    return df_encoded, encoders


def create_correlation_matrix(df: pd.DataFrame, target_column: str = None) -> go.Figure:
    """상관관계 매트릭스 생성"""
    # 수치형 컬럼만 선택
    numeric_df = df.select_dtypes(include=[np.number])
    
    if numeric_df.empty:
        return None
    
    correlation_matrix = numeric_df.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=correlation_matrix.round(3),
        texttemplate="%{text}",
        textfont={"size": 10},
    ))
    
    fig.update_layout(
        title="특성 간 상관관계 매트릭스",
        width=600,
        height=500
    )
    
    return fig


def create_feature_importance_plot(model, feature_names: List[str]) -> go.Figure:
    """특성 중요도 플롯 생성"""
    if not hasattr(model, 'feature_importances_'):
        return None
    
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=True)
    
    fig = px.bar(
        importance_df,
        x='Importance',
        y='Feature',
        orientation='h',
        title="특성 중요도"
    )
    
    fig.update_layout(height=400)
    
    return fig


def generate_sample_data(n_samples: int = 50) -> pd.DataFrame:
    """샘플 데이터 생성"""
    np.random.seed(42)
    
    promoters = ['P1', 'P2', 'P3', 'P4']
    genes = ['Gene_A', 'Gene_B', 'Gene_C', 'Gene_D']
    
    data = {
        'Promoter': np.random.choice(promoters, n_samples),
        'CDS': np.random.choice(genes, n_samples),
        'Temperature': np.random.normal(30, 3, n_samples),
        'pH': np.random.normal(7.0, 0.5, n_samples),
        'Inducer_Conc': np.random.uniform(0.1, 1.0, n_samples),
    }
    
    # 타겟 변수 생성 (특성들의 비선형 조합)
    df = pd.DataFrame(data)
    
    # 범주형 변수를 수치로 변환하여 타겟 계산
    promoter_effect = {'P1': 1.0, 'P2': 1.2, 'P3': 0.8, 'P4': 1.1}
    gene_effect = {'Gene_A': 1.0, 'Gene_B': 1.3, 'Gene_C': 0.9, 'Gene_D': 1.1}
    
    df['Promoter_Effect'] = df['Promoter'].map(promoter_effect)
    df['Gene_Effect'] = df['CDS'].map(gene_effect)
    
    # 비선형 효과 추가
    temperature_effect = 1 + 0.05 * (df['Temperature'] - 30) - 0.002 * (df['Temperature'] - 30)**2
    pH_effect = 1 + 0.2 * (df['pH'] - 7.0) - 0.1 * (df['pH'] - 7.0)**2
    
    df['Expression_Level'] = (100 * df['Promoter_Effect'] * df['Gene_Effect'] * 
                             temperature_effect * pH_effect * df['Inducer_Conc'] +
                             np.random.normal(0, 5, n_samples))
    
    # 불필요한 중간 컬럼 제거
    df = df.drop(['Promoter_Effect', 'Gene_Effect'], axis=1)
    
    # 음수값 제거
    df['Expression_Level'] = np.maximum(df['Expression_Level'], 10)
    
    return df


def create_pairplot(df: pd.DataFrame, target_column: str = None) -> go.Figure:
    """페어플롯 생성 (간소화된 버전)"""
    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_columns) < 2:
        return None
    
    # 최대 4개 컬럼만 사용
    if len(numeric_columns) > 4:
        numeric_columns = numeric_columns[:4]
    
    n_cols = len(numeric_columns)
    
    fig = make_subplots(
        rows=n_cols, cols=n_cols,
        subplot_titles=[f"{col1} vs {col2}" for col1 in numeric_columns for col2 in numeric_columns]
    )
    
    for i, col1 in enumerate(numeric_columns):
        for j, col2 in enumerate(numeric_columns):
            if i == j:
                # 대각선: 히스토그램
                fig.add_trace(
                    go.Histogram(x=df[col1], name=f"{col1} dist"),
                    row=i+1, col=j+1
                )
            else:
                # 비대각선: 산점도
                fig.add_trace(
                    go.Scatter(
                        x=df[col2], y=df[col1], 
                        mode='markers',
                        name=f"{col1} vs {col2}"
                    ),
                    row=i+1, col=j+1
                )
    
    fig.update_layout(
        height=200 * n_cols,
        title="특성 간 관계 분석",
        showlegend=False
    )
    
    return fig


def calculate_experiment_statistics(df: pd.DataFrame, target_column: str) -> Dict:
    """실험 통계 계산"""
    stats = {
        'sample_count': len(df),
        'target_mean': df[target_column].mean(),
        'target_std': df[target_column].std(),
        'target_min': df[target_column].min(),
        'target_max': df[target_column].max(),
        'missing_values': df.isnull().sum().sum(),
        'categorical_features': len(df.select_dtypes(include=['object']).columns),
        'numerical_features': len(df.select_dtypes(include=[np.number]).columns) - 1,  # 타겟 제외
    }
    
    return stats


def format_number(num: float, decimals: int = 2) -> str:
    """숫자 포맷팅"""
    if abs(num) >= 1000:
        return f"{num:,.{decimals}f}"
    else:
        return f"{num:.{decimals}f}"


def create_optimization_progress_plot(optimization_results: List[Tuple]) -> go.Figure:
    """최적화 진행 과정 시각화"""
    if not optimization_results:
        return None
    
    iterations = list(range(1, len(optimization_results) + 1))
    values = [result[1] for result in optimization_results]
    
    # 누적 최대값 계산
    cumulative_max = []
    current_max = float('-inf')
    for value in values:
        if value > current_max:
            current_max = value
        cumulative_max.append(current_max)
    
    fig = go.Figure()
    
    # 모든 시도값
    fig.add_trace(go.Scatter(
        x=iterations,
        y=values,
        mode='markers',
        name='시도값',
        marker=dict(color='lightblue', size=8)
    ))
    
    # 누적 최대값
    fig.add_trace(go.Scatter(
        x=iterations,
        y=cumulative_max,
        mode='lines+markers',
        name='최적값 진행',
        line=dict(color='red', width=2)
    ))
    
    fig.update_layout(
        title="베이지안 최적화 진행 과정",
        xaxis_title="반복 횟수",
        yaxis_title="목적 함수 값",
        hovermode='x unified'
    )
    
    return fig


def create_parameter_sensitivity_plot(optimizer, parameter_name: str, n_points: int = 50) -> go.Figure:
    """파라미터 민감도 분석 플롯"""
    if optimizer is None or not hasattr(optimizer, 'bounds'):
        return None
    
    if parameter_name not in optimizer.bounds:
        return None
    
    param_min, param_max = optimizer.bounds[parameter_name]
    param_values = np.linspace(param_min, param_max, n_points)
    
    # 다른 파라미터들은 최적값으로 고정
    best_params = optimizer.optimizer.max['params'].copy()
    objective_values = []
    
    for param_val in param_values:
        test_params = best_params.copy()
        test_params[parameter_name] = param_val
        
        try:
            obj_val = optimizer.objective_function(**test_params)
            objective_values.append(obj_val)
        except:
            objective_values.append(np.nan)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=param_values,
        y=objective_values,
        mode='lines+markers',
        name=f'{parameter_name} 민감도'
    ))
    
    # 최적값 표시
    fig.add_vline(
        x=best_params[parameter_name],
        line_dash="dash",
        line_color="red",
        annotation_text="최적값"
    )
    
    fig.update_layout(
        title=f"{parameter_name} 파라미터 민감도 분석",
        xaxis_title=parameter_name,
        yaxis_title="예측값"
    )
    
    return fig