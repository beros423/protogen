import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler, LabelEncoder, PolynomialFeatures
from sklearn.model_selection import cross_val_score
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.pipeline import Pipeline
import joblib
from typing import Dict, Tuple, List, Any
from bayes_opt import BayesianOptimization
import warnings
warnings.filterwarnings('ignore')


class MLModelTrainer:
    def __init__(self, model_preference='linear_focused', encoding_method='auto', target_transform='auto'):
        """
        베타카로틴 생산 최적화를 위한 ML 모델 트레이너
        
        Parameters:
        -----------
        model_preference : str
            'linear_focused': 선형 모델 중심 (소규모/노이즈 많은 데이터에 적합)
            'ensemble_focused': 앙상블 모델 중심 (대규모 데이터에 적합)
            'all': 모든 모델 비교
        
        encoding_method : str
            'auto': 자동 선택 (One-Hot 우선)
            'label': Label Encoding
            'onehot': One-Hot Encoding
            'onehot_drop': One-Hot Encoding with drop_first
        
        target_transform : str
            'auto': 자동 선택 (분포 분석 기반)
            'none': 변환 없음
            'log': Log 변환
            'sqrt': Square Root 변환
        """
        self.model_preference = model_preference
        self.encoding_method = encoding_method
        self.target_transform = target_transform
        
        # 모델 설정
        if model_preference == 'linear_focused':
            self.models = {
                'linear_regression': LinearRegression(),
                'ridge_regression': Ridge(alpha=1.0, random_state=42),
                'lasso_regression': Lasso(alpha=0.1, random_state=42, max_iter=2000),
                'elastic_net': ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42, max_iter=2000),
                'polynomial_regression': Pipeline([
                    ('poly', PolynomialFeatures(degree=2, include_bias=False)),
                    ('linear', LinearRegression())
                ])
            }
        elif model_preference == 'ensemble_focused':
            self.models = {
                'random_forest': RandomForestRegressor(random_state=42, n_estimators=100),
                'gradient_boosting': GradientBoostingRegressor(random_state=42, n_estimators=100),
                'linear_regression': LinearRegression()
            }
        else:  # 'all'
            self.models = {
                'linear_regression': LinearRegression(),
                'ridge_regression': Ridge(alpha=1.0, random_state=42),
                'lasso_regression': Lasso(alpha=0.1, random_state=42, max_iter=2000),
                'elastic_net': ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42, max_iter=2000),
                'random_forest': RandomForestRegressor(random_state=42, n_estimators=50),
                'gradient_boosting': GradientBoostingRegressor(random_state=42, n_estimators=50),
            }
        
        # 초기화
        self.best_model = None
        self.best_score = float('-inf')
        self.best_model_name = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.categorical_columns = []
        self.numerical_columns = []
        self.feature_names = []
        self.target_name = ""
        self.target_transformer = None
        self.is_target_transformed = False
        
        # 전처리기 저장용 (예측 시 사용)
        self.encoder = None  # One-Hot 인코더
        self.encoders = {}   # Label 인코더들
        self.final_encoding_method = None  # 실제 사용된 인코딩 방법
    
    def preprocess_data(self, df: pd.DataFrame, target_column: str, feature_columns: list = None) -> Tuple[np.ndarray, np.ndarray]:
        """데이터 전처리 및 특성 엔지니어링"""
        # 데이터 복사
        df_clean = df.copy()
        
        # 1. 결측값 확인
        print(f"원본 데이터 크기: {df_clean.shape}")
        missing_info = df_clean.isnull().sum()
        if missing_info.sum() > 0:
            print(f"결측값 확인:")
            print(missing_info[missing_info > 0])
        
        # 2. 특성 컬럼 선택
        if feature_columns is None:
            # 자동 특성 선택
            exclude_columns = [target_column, 'Unnamed: 0']
            exclude_columns.extend([col for col in df_clean.columns if 'unnamed' in col.lower()])
            exclude_columns = [col for col in exclude_columns if col in df_clean.columns]
            available_columns = [col for col in df_clean.columns if col not in exclude_columns]
            print(f"🔍 자동 선택된 특성: {available_columns}")
        else:
            # 사용자 지정 특성
            available_columns = [col for col in feature_columns if col in df_clean.columns]
            print(f"🎯 사용자 선택 특성: {feature_columns}")
            print(f"✅ 실제 사용 가능한 특성: {available_columns}")
        
        if len(available_columns) == 0:
            raise ValueError("사용할 수 있는 특성 컬럼이 없습니다!")
        
        # 타겟 변수 결측값 처리
        if df_clean[target_column].isnull().any():
            print(f"타겟 변수 '{target_column}'에 결측값 제거")
            df_clean = df_clean.dropna(subset=[target_column])
        
        X = df_clean[available_columns]
        y = df_clean[target_column]
        
        # 특성 이름 저장
        self.feature_names = list(X.columns)
        self.target_name = target_column
        print(f"✓ 저장된 특성 이름: {self.feature_names}")
        print(f"✓ 타겟 변수: {self.target_name}")
        
        # 3. 결측값 처리
        for column in X.columns:
            if X[column].isnull().any():
                if X[column].dtype == 'object':
                    mode_value = X[column].mode()[0] if not X[column].mode().empty else 'Unknown'
                    X[column] = X[column].fillna(mode_value)
                    print(f"범주형 변수 '{column}' 결측값을 '{mode_value}'로 채움")
                else:
                    median_value = X[column].median()
                    X[column] = X[column].fillna(median_value)
                    print(f"수치형 변수 '{column}' 결측값을 {median_value}로 채움")
        
        # 4. 범주형/수치형 구분
        self.categorical_columns = [col for col in X.columns if X[col].dtype == 'object']
        self.numerical_columns = [col for col in X.columns if X[col].dtype != 'object']
        
        print(f"📊 범주형 컬럼 ({len(self.categorical_columns)}개): {self.categorical_columns}")
        print(f"🔢 수치형 컬럼 ({len(self.numerical_columns)}개): {self.numerical_columns}")
        
        # 5. 인코딩 방법 자동 선택
        if self.encoding_method == 'auto':
            n_samples, n_features = X.shape
            total_categories = sum(X[col].nunique() for col in self.categorical_columns) if self.categorical_columns else 0
            
            # 기본적으로 One-Hot 인코딩 사용 (생물학적 데이터에 더 적합)
            if n_samples < 50 or total_categories > n_samples / 3:
                chosen_encoding = 'label'
                print(f"🔄 자동 선택: Label Encoding (샘플:{n_samples}, 범주수:{total_categories})")
            else:
                chosen_encoding = 'onehot_drop'
                print(f"🔄 자동 선택: One-Hot Encoding (생물학적 데이터 권장)")
        else:
            chosen_encoding = self.encoding_method
        
        print(f"✅ 사용할 인코딩: {chosen_encoding}")
        
        # 6. 범주형 변수 인코딩
        self.final_encoding_method = chosen_encoding
        
        if chosen_encoding == 'label':
            for column in self.categorical_columns:
                if column not in self.label_encoders:
                    self.label_encoders[column] = LabelEncoder()
                X[column] = self.label_encoders[column].fit_transform(X[column].astype(str))
            
            # Label 인코더 저장
            self.encoders = self.label_encoders.copy()
        
        elif chosen_encoding in ['onehot', 'onehot_drop']:
            if self.categorical_columns:
                from sklearn.preprocessing import OneHotEncoder
                
                drop_first = (chosen_encoding == 'onehot_drop')
                
                # OneHotEncoder 사용하여 변환 및 저장
                self.encoder = OneHotEncoder(drop='first' if drop_first else None, sparse_output=False)
                X_categorical = X[self.categorical_columns]
                X_numerical = X[self.numerical_columns] if self.numerical_columns else pd.DataFrame()
                
                # 인코더 학습 및 변환
                X_encoded_array = self.encoder.fit_transform(X_categorical)
                
                # 특성 이름 생성
                feature_names_encoded = self.encoder.get_feature_names_out(self.categorical_columns)
                X_encoded = pd.DataFrame(X_encoded_array, columns=feature_names_encoded, index=X.index)
                
                if not X_numerical.empty:
                    X = pd.concat([X_numerical, X_encoded], axis=1)
                else:
                    X = X_encoded
                
                self.feature_names = list(X.columns)
                print(f"🔄 One-Hot 인코딩 완료: {len(self.feature_names)}개 특성 생성")
        
        # 7. 무한대값 처리
        X = X.replace([np.inf, -np.inf], np.nan)
        if X.isnull().any().any():
            print("무한대 값을 NaN으로 변환 후 중앙값으로 채움")
            for column in X.columns:
                if X[column].isnull().any():
                    X[column] = X[column].fillna(X[column].median())
        
        # 8. 타겟 변수 변환
        y_transformed = self._transform_target(y)
        
        # 9. 특성 스케일링
        X_scaled = self.scaler.fit_transform(X)
        
        print(f"전처리 완료 - 최종 데이터 크기: {X_scaled.shape}, 타겟 크기: {y_transformed.shape}")
        
        return X_scaled, y_transformed
    
    def _transform_target(self, y: pd.Series) -> np.ndarray:
        """타겟 변수 변환"""
        if self.target_transform == 'auto':
            # 데이터 분포 분석
            y_min, y_max = y.min(), y.max()
            skewness = y.skew()
            zero_count = (y == 0).sum()
            
            print(f"📊 타겟 변수 분포 분석:")
            print(f"  - 범위: {y_min:.3f} ~ {y_max:.3f}")
            print(f"  - 왜도: {skewness:.3f}")
            print(f"  - 0값 개수: {zero_count}/{len(y)}")
            
            # 자동 변환 선택
            if skewness > 1.0 and zero_count > 0:
                chosen_transform = 'log'
                print(f"🔄 자동 선택: log 변환 (높은 왜도 + 0값 존재)")
            elif skewness > 1.0:
                chosen_transform = 'sqrt'
                print(f"🔄 자동 선택: sqrt 변환 (높은 왜도)")
            else:
                chosen_transform = 'none'
                print(f"🔄 자동 선택: 변환 없음 (정규분포에 가까움)")
        else:
            chosen_transform = self.target_transform
        
        print(f"✅ 타겟 변환 방법: {chosen_transform}")
        
        # 실제 사용된 변환 방법 저장
        self.final_target_transform = chosen_transform
        
        # 변환 수행
        if chosen_transform == 'log':
            y_transformed = np.log1p(y.values)
            self.target_transformer = 'log'
            self.is_target_transformed = True
            print(f"  📈 log(y + 1) 변환 완료: {y.min():.3f}~{y.max():.3f} → {y_transformed.min():.3f}~{y_transformed.max():.3f}")
        
        elif chosen_transform == 'sqrt':
            if y.min() < 0:
                offset = -y.min() + 1e-8
                y_transformed = np.sqrt(y.values + offset)
                self.target_transformer = ('sqrt_offset', offset)
                print(f"  📈 sqrt(y + {offset:.6f}) 변환 완료")
            else:
                y_transformed = np.sqrt(y.values)
                self.target_transformer = 'sqrt'
                print(f"  📈 sqrt(y) 변환 완료: {y.min():.3f}~{y.max():.3f} → {y_transformed.min():.3f}~{y_transformed.max():.3f}")
            
            self.is_target_transformed = True
        
        else:  # 'none'
            y_transformed = y.values
            self.target_transformer = None
            self.is_target_transformed = False
            print(f"  📈 변환 없음")
        
        return y_transformed
    
    def _inverse_transform_target(self, y_pred: np.ndarray) -> np.ndarray:
        """타겟 변수 역변환"""
        if not self.is_target_transformed:
            return y_pred
        
        if self.target_transformer == 'log':
            return np.expm1(y_pred)
        elif self.target_transformer == 'sqrt':
            return y_pred ** 2
        elif isinstance(self.target_transformer, tuple) and self.target_transformer[0] == 'sqrt_offset':
            offset = self.target_transformer[1]
            return (y_pred ** 2) - offset
        else:
            return y_pred
    
    def train_models(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """모델 학습 및 평가"""
        results = {}
        
        print(f"\n🔍 모델 학습 디버깅 정보:")
        print(f"📊 입력 데이터 형태: X={X.shape}, y={y.shape}")
        print(f"📈 타겟 통계:")
        print(f"  - 범위: {np.min(y):.4f} ~ {np.max(y):.4f}")
        print(f"  - 평균: {np.mean(y):.4f} ± {np.std(y):.4f}")
        print(f"  - 중앙값: {np.median(y):.4f}")
        
        # 베이스라인 점수
        dummy_predictions = np.full_like(y, np.mean(y))
        baseline_r2 = 1 - np.sum((y - dummy_predictions)**2) / np.sum((y - np.mean(y))**2)
        print(f"📊 베이스라인 (평균 예측) R²: {baseline_r2:.4f}")
        
        for name, model in self.models.items():
            try:
                print(f"\n🤖 {name} 학습 중...")
                
                # 교차 검증
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
                mean_score = cv_scores.mean()
                std_score = cv_scores.std()
                results[name] = mean_score
                
                print(f"  📈 CV 점수: {[f'{score:.4f}' for score in cv_scores]}")
                print(f"  📊 평균: {mean_score:.4f} ± {std_score:.4f}")
                
                # 모델 복잡도 확인
                model.fit(X, y)
                train_score = model.score(X, y)
                print(f"  🎯 훈련 점수: {train_score:.4f}")
                
                # 과적합 판단
                if train_score - mean_score > 0.1:
                    print(f"  ⚠️  과적합 가능성 (훈련-검증 차이: {train_score - mean_score:.4f})")
                elif train_score < 0.1:
                    print(f"  ⚠️  과소적합 가능성")
                
                # 최고 성능 모델 저장
                if mean_score > self.best_score:
                    self.best_score = mean_score
                    self.best_model = model
                    self.best_model_name = name
                    print(f"  🏆 새로운 최고 성능 모델!")
                
            except Exception as e:
                print(f"❌ 모델 {name} 학습 중 오류: {str(e)}")
                results[name] = -999.0
        
        # 최종 결과
        if self.best_model is not None:
            print(f"\n🎯 최종 선택된 모델: {self.best_model_name}")
            print(f"🎯 최고 성능: R² = {self.best_score:.4f}")
        
        return results
    
    def predict(self, X_new: np.ndarray) -> np.ndarray:
        """새로운 데이터 예측"""
        if self.best_model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        
        predictions = self.best_model.predict(X_new)
        
        # 타겟 변환이 적용된 경우 역변환
        if self.is_target_transformed:
            predictions = self._inverse_transform_target(predictions)
        
        return predictions
    
    def save_model(self, filepath: str):
        """모델 저장"""
        model_data = {
            'best_model': self.best_model,
            'best_model_name': self.best_model_name,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'target_name': self.target_name,
            'best_score': self.best_score,
            'target_transformer': self.target_transformer,
            'is_target_transformed': self.is_target_transformed
        }
        joblib.dump(model_data, filepath)
        print(f"모델이 저장되었습니다: {filepath}")
    
    def load_model(self, filepath: str):
        """모델 로드"""
        model_data = joblib.load(filepath)
        self.best_model = model_data['best_model']
        self.best_model_name = model_data.get('best_model_name', 'Unknown')
        self.scaler = model_data['scaler']
        self.label_encoders = model_data['label_encoders']
        self.feature_names = model_data['feature_names']
        self.target_name = model_data['target_name']
        self.best_score = model_data.get('best_score', 0.0)
        self.target_transformer = model_data.get('target_transformer', None)
        self.is_target_transformed = model_data.get('is_target_transformed', False)
        print(f"모델이 로드되었습니다: {filepath}")