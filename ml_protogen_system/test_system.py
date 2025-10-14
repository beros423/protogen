import pandas as pd
import numpy as np
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_core import MLModelTrainer, BayesianOptimizer, MappingFileGenerator
from utils import generate_sample_data, validate_dataframe


def test_ml_trainer():
    """ML 모델 학습 테스트"""
    print("Testing ML Model Trainer...")
    
    # 샘플 데이터 생성
    df = generate_sample_data(30)
    target_column = 'Expression_Level'
    
    # 모델 학습
    trainer = MLModelTrainer()
    X, y = trainer.preprocess_data(df, target_column)
    results = trainer.train_models(X, y)
    
    print(f"Model training results: {results}")
    print(f"Best score: {trainer.best_score:.4f}")
    
    # 예측 테스트
    predictions = trainer.predict(X[:5])
    print(f"Sample predictions: {predictions}")
    
    return trainer


def test_bayesian_optimizer(trainer):
    """베이지안 최적화 테스트"""
    print("\nTesting Bayesian Optimizer...")
    
    # 옵티마이저 설정
    optimizer = BayesianOptimizer(trainer)
    
    # 범위 설정
    bounds = {
        'Temperature': (25.0, 40.0),
        'pH': (6.0, 8.0),
        'Inducer_Conc': (0.1, 1.0)
    }
    
    categorical_features = {
        'Promoter': ['P1', 'P2', 'P3', 'P4'],
        'CDS': ['Gene_A', 'Gene_B', 'Gene_C', 'Gene_D']
    }
    
    optimizer.set_bounds(bounds)
    optimizer.set_categorical_features(categorical_features)
    
    # 최적화 실행
    results = optimizer.optimize(n_iter=5)
    
    print(f"Optimization results: {results['best_params']}")
    print(f"Best value: {results['best_value']:.4f}")
    
    # 실험 제안
    suggestions = optimizer.suggest_experiments(3)
    print(f"Experiment suggestions: {suggestions}")
    
    return optimizer


def test_mapping_generator():
    """매핑 파일 생성 테스트"""
    print("\nTesting Mapping File Generator...")
    
    # 샘플 실험 데이터
    experiments = [
        {'Promoter': 'P1', 'CDS': 'Gene_A', 'Temperature': 30.5, 'pH': 7.1},
        {'Promoter': 'P2', 'CDS': 'Gene_B', 'Temperature': 32.0, 'pH': 7.3},
        {'Promoter': 'P3', 'CDS': 'Gene_C', 'Temperature': 28.5, 'pH': 6.9},
    ]
    
    generator = MappingFileGenerator()
    
    # 매핑 파일 생성
    mapping_df = generator.create_mapping_file(experiments, plate_type=96)
    print("Generated mapping file:")
    print(mapping_df)
    
    # 프로토콜 파일 생성
    protocol_df = generator.create_protocol_file(mapping_df)
    print("\nGenerated protocol file:")
    print(protocol_df.head())
    
    return generator


def test_utils():
    """유틸리티 함수 테스트"""
    print("\nTesting utility functions...")
    
    # 샘플 데이터 생성 테스트
    df = generate_sample_data(20)
    print(f"Generated sample data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # 검증 테스트
    is_valid = validate_dataframe(df, ['Promoter', 'Expression_Level'])
    print(f"Data validation result: {is_valid}")
    
    return True


def main():
    """전체 시스템 테스트"""
    print("ML Protogen System - Component Testing")
    print("=" * 50)
    
    try:
        # 각 컴포넌트 테스트
        trainer = test_ml_trainer()
        optimizer = test_bayesian_optimizer(trainer)
        generator = test_mapping_generator()
        test_utils()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("The system is ready to use.")
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        print("Please check the installation and dependencies.")
        return False
    
    return True


if __name__ == "__main__":
    main()