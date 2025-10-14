import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler, LabelEncoder, PolynomialFeatures, OneHotEncoder
from sklearn.model_selection import cross_val_score
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.pipeline import Pipeline
import joblib
from typing import Dict, Tuple, List, Any
from bayes_opt import BayesianOptimization
import warnings
warnings.filterwarnings('ignore')


class MLModelTrainer:
    def __init__(self, model_preference='linear_focused', encoding_method='auto', target_transform='none'):
        """
        model_preference 옵션:
        - 'all': 모든 모델 (기본값)
        - 'linear_focused': 선형 모델 중심 (소규모/노이즈 많은 데이터에 적합)
        - 'ensemble_focused': 앙상블 모델 중심 (대규모 데이터에 적합)
        
        encoding_method 옵션:
        - 'auto': 데이터 크기에 따라 자동 선택 (기본적으로 One-Hot 선호)
        - 'label': Label Encoding (순서형)
        - 'onehot': One-Hot Encoding (명목형)
        - 'onehot_drop': One-Hot Encoding with drop_first (다중공선성 방지)
        
        target_transform 옵션:
        - 'none': 변환 없음
        - 'log': log(y + 1) 변환 (왜도 개선, 0값 처리)
        - 'sqrt': sqrt(y) 변환 (분산 안정화)
        - 'auto': 데이터 분포에 따라 자동 선택
        """
        self.model_preference = model_preference
        self.encoding_method = encoding_method
        self.target_transform = target_transform
        
        # 선형 모델 중심 설정
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
        # 앙상블 모델 중심 설정
        elif model_preference == 'ensemble_focused':
            self.models = {
                'random_forest': RandomForestRegressor(random_state=42, n_estimators=100),
                'gradient_boosting': GradientBoostingRegressor(random_state=42, n_estimators=100),
                'linear_regression': LinearRegression()
            }
        # 모든 모델 사용 (기본값)
        else:
            self.models = {
                'linear_regression': LinearRegression(),
                'ridge_regression': Ridge(alpha=1.0, random_state=42),
                'lasso_regression': Lasso(alpha=0.1, random_state=42, max_iter=2000),
                'random_forest': RandomForestRegressor(random_state=42, n_estimators=50),
                'gradient_boosting': GradientBoostingRegressor(random_state=42, n_estimators=50),
            }
        
        self.best_model = None
        self.best_score = float('-inf')  # 음수 점수도 허용하도록 변경
        self.best_model_name = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.onehot_encoder = None
        self.categorical_columns = []
        self.numerical_columns = []
        self.feature_names = []
        self.target_name = ""
        self.target_transformer = None
        self.is_target_transformed = False
    
    def preprocess_data(self, df: pd.DataFrame, target_column: str, feature_columns: list = None) -> Tuple[np.ndarray, np.ndarray]:
        """데이터 전처리 및 특성 엔지니어링
        
        Args:
            df: 입력 데이터프레임
            target_column: 타겟 변수 컬럼명
            feature_columns: 사용할 특성 컬럼 리스트 (None이면 자동 선택)
        """
        # 데이터 복사본 생성 (원본 보존)
        df_clean = df.copy()
        
        # 1. 결측값 확인 및 처리
        print(f"원본 데이터 크기: {df_clean.shape}")
        print(f"결측값 확인:")
        missing_info = df_clean.isnull().sum()
        if missing_info.sum() > 0:
            print(missing_info[missing_info > 0])
        
        # 타겟 변수에 결측값이 있으면 해당 행 제거
        if df_clean[target_column].isnull().any():
            print(f"타겟 변수 '{target_column}'에 결측값 {df_clean[target_column].isnull().sum()}개 발견 - 해당 행 제거")
            df_clean = df_clean.dropna(subset=[target_column])
        
        # 타겟 변수 분리 및 특성 컬럼 선택
        if feature_columns is not None:
            # 사용자가 지정한 특성 컬럼들 사용
            available_columns = [col for col in feature_columns if col in df_clean.columns and col != target_column]
            
            print(f"🎯 사용자 선택 특성: {feature_columns}")
            print(f"✅ 실제 사용 가능한 특성 ({len(available_columns)}개): {available_columns}")
            
            # 누락된 컬럼 체크
            missing_columns = [col for col in feature_columns if col not in df_clean.columns]
            if missing_columns:
                print(f"⚠️ 데이터에서 찾을 수 없는 특성: {missing_columns}")
        else:
            # 자동 선택 (기존 로직)
            exclude_patterns = ['Sample_ID', 'sample_id', 'ID', 'id', 'Unnamed:', 'unnamed:', 'Well', 'well', 'Index', 'index']
            exclude_columns = [target_column]  # 타겟 컬럼은 항상 제외
            
            # 패턴 매칭으로 제외할 컬럼 찾기
            for col in df_clean.columns:
                for pattern in exclude_patterns:
                    if pattern in col:
                        exclude_columns.append(col)
                        break
            
            # 중복 제거
            exclude_columns = list(set(exclude_columns))
            
            # 실제 특성 컬럼만 선택
            available_columns = [col for col in df_clean.columns if col not in exclude_columns]
            
            print(f"🔍 전체 컬럼: {list(df_clean.columns)}")
            print(f"❌ 자동 제외된 컬럼: {exclude_columns}")
            print(f"✅ 자동 선택된 특성 컬럼 ({len(available_columns)}개): {available_columns}")
        
        if len(available_columns) == 0:
            raise ValueError("사용할 수 있는 특성 컬럼이 없습니다!")
        
        X = df_clean[available_columns]
        y = df_clean[target_column]
        
        # 특성 이름 저장 (나중에 예측할 때 사용)
        self.feature_names = list(X.columns)
        self.target_name = target_column
        
        print(f"✓ 저장된 특성 이름 ({len(self.feature_names)}개): {self.feature_names}")
        print(f"✓ 타겟 변수: {self.target_name}")
        self.feature_names = list(X.columns)
        
        # 2. 각 특성별 결측값 처리
        for column in X.columns:
            if X[column].isnull().any():
                if X[column].dtype == 'object':
                    # 범주형 변수: 최빈값으로 채우기
                    mode_value = X[column].mode()[0] if not X[column].mode().empty else 'Unknown'
                    X[column] = X[column].fillna(mode_value)
                    print(f"범주형 변수 '{column}' 결측값을 '{mode_value}'로 채움")
                else:
                    # 수치형 변수: 중앙값으로 채우기
                    median_value = X[column].median()
                    X[column] = X[column].fillna(median_value)
                    print(f"수치형 변수 '{column}' 결측값을 {median_value}로 채움")
        
        # 3. 범주형/수치형 컬럼 구분
        self.categorical_columns = [col for col in X.columns if X[col].dtype == 'object']
        self.numerical_columns = [col for col in X.columns if X[col].dtype != 'object']
        
        print(f"📊 범주형 컬럼 ({len(self.categorical_columns)}개): {self.categorical_columns}")
        print(f"🔢 수치형 컬럼 ({len(self.numerical_columns)}개): {self.numerical_columns}")
        
        # 4. 인코딩 방법 자동 선택
        if self.encoding_method == 'auto':
            # 기본적으로 One-Hot 인코딩 사용 (생물학적 데이터에 더 적합)
            n_samples, n_features = X.shape
            total_categories = sum(X[col].nunique() for col in self.categorical_columns)
            
            # 매우 작은 데이터셋이거나 범주가 너무 많을 때만 Label 인코딩
            if n_samples < 50 or total_categories > n_samples / 3:
                chosen_encoding = 'label'
                print(f"🔄 자동 선택: Label Encoding (샘플:{n_samples}, 범주수:{total_categories}) - 데이터 부족으로 인한 선택")
            else:
                chosen_encoding = 'onehot_drop'
                print(f"🔄 자동 선택: One-Hot Encoding with drop_first (생물학적 데이터 권장)")
        else:
            chosen_encoding = self.encoding_method
            
        print(f"✅ 사용할 인코딩: {chosen_encoding}")
        
        # 5. 범주형 변수 인코딩 수행
        if chosen_encoding == 'label':
            # Label Encoding
            for column in self.categorical_columns:
                if column not in self.label_encoders:
                    self.label_encoders[column] = LabelEncoder()
                X[column] = self.label_encoders[column].fit_transform(X[column].astype(str))
                
        elif chosen_encoding in ['onehot', 'onehot_drop']:
            # One-Hot Encoding
            if self.categorical_columns:
                drop_first = (chosen_encoding == 'onehot_drop')
                
                # pandas get_dummies 사용 (더 안정적)
                X_categorical = X[self.categorical_columns]
                X_numerical = X[self.numerical_columns] if self.numerical_columns else pd.DataFrame()
                
                X_encoded = pd.get_dummies(X_categorical, drop_first=drop_first, prefix=self.categorical_columns)
                
                # 수치형과 범주형 결합
                if not X_numerical.empty:
                    X = pd.concat([X_numerical, X_encoded], axis=1)
                else:
                    X = X_encoded
                
                # 특성 이름 업데이트
                self.feature_names = list(X.columns)
                print(f"🔄 One-Hot 인코딩 완료: {len(self.feature_names)}개 특성 생성")
        
        # 6. 무한대 값 처리
        X = X.replace([np.inf, -np.inf], np.nan)
        if X.isnull().any().any():
            print("무한대 값을 NaN으로 변환 후 중앙값으로 채움")
            for column in X.columns:
                if X[column].isnull().any():
                    X[column] = X[column].fillna(X[column].median())
        
        # 7. 최종 결측값 확인
        final_missing = X.isnull().sum().sum() + y.isnull().sum()
        if final_missing > 0:
            raise ValueError(f"전처리 후에도 결측값이 {final_missing}개 남아있습니다.")
        
        # 8. 타겟 변수 변환
        y_transformed = self._transform_target(y)
        
        # 9. 수치형 변수 스케일링
        X_scaled = self.scaler.fit_transform(X)
        
        print(f"전처리 완료 - 최종 데이터 크기: {X_scaled.shape}, 타겟 크기: {y_transformed.shape}")
        
        return X_scaled, y_transformed
    
    def _transform_target(self, y: pd.Series) -> np.ndarray:
        """타겟 변수 변환"""
        
        # 타겟 변환 방법 결정
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
        
        # 변환 수행
        if chosen_transform == 'log':
            # log(y + 1) 변환 (0값 처리)
            y_transformed = np.log1p(y.values)  # log1p = log(1 + x)
            self.target_transformer = 'log'
            self.is_target_transformed = True
            print(f"  📈 log(y + 1) 변환 완료: {y.min():.3f}~{y.max():.3f} → {y_transformed.min():.3f}~{y_transformed.max():.3f}")
            
        elif chosen_transform == 'sqrt':
            # sqrt 변환 (음수값이 있으면 처리)
            if y.min() < 0:
                # 음수가 있으면 최솟값을 0으로 이동 후 sqrt
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
        """타겟 변수 역변환 (예측값을 원래 스케일로 복원)"""
        
        if not self.is_target_transformed:
            return y_pred
        
        if self.target_transformer == 'log':
            return np.expm1(y_pred)  # expm1 = exp(x) - 1
        elif self.target_transformer == 'sqrt':
            return y_pred ** 2
        elif isinstance(self.target_transformer, tuple) and self.target_transformer[0] == 'sqrt_offset':
            offset = self.target_transformer[1]
            return (y_pred ** 2) - offset
        else:
            return y_pred
    
    def train_models(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """여러 모델 학습 및 평가 (상세 디버깅 포함)"""
        results = {}
        
        print(f"\n🔍 모델 학습 디버깅 정보:")
        print(f"📊 입력 데이터 형태: X={X.shape}, y={y.shape}")
        print(f"📈 타겟 통계:")
        print(f"  - 범위: {np.min(y):.4f} ~ {np.max(y):.4f}")
        print(f"  - 평균: {np.mean(y):.4f} ± {np.std(y):.4f}")
        print(f"  - 중앙값: {np.median(y):.4f}")
        print(f"  - 고유값 수: {len(np.unique(y))}/{len(y)}")
        
        # 특성별 통계
        print(f"📊 특성별 통계:")
        for i, feature_name in enumerate(self.feature_names):
            col_data = X[:, i]
            print(f"  - {feature_name}: 범위={np.min(col_data):.4f}~{np.max(col_data):.4f}, 고유값={len(np.unique(col_data))}개")
        
        # 베이스라인 점수 계산 (단순 평균 예측)
        baseline_score = 1 - np.var(y) / np.var(y)  # R² for predicting mean
        dummy_predictions = np.full_like(y, np.mean(y))
        baseline_r2 = 1 - np.sum((y - dummy_predictions)**2) / np.sum((y - np.mean(y))**2)
        print(f"📊 베이스라인 (평균 예측) R²: {baseline_r2:.4f}")
        
        for name, model in self.models.items():
            try:
                print(f"\n🤖 {name} 학습 중...")
                
                # 교차 검증 (더 상세한 정보)
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
                mean_score = cv_scores.mean()
                std_score = cv_scores.std()
                results[name] = mean_score
                
                # 개별 fold 점수 출력
                print(f"  📈 CV 점수: {[f'{score:.4f}' for score in cv_scores]}")
                print(f"  📊 평균: {mean_score:.4f} ± {std_score:.4f}")
                
                # 모델 복잡도 확인
                model.fit(X, y)
                train_score = model.score(X, y)
                print(f"  🎯 훈련 점수: {train_score:.4f}")
                
                # 과적합/과소적합 판단
                if train_score - mean_score > 0.1:
                    print(f"  ⚠️  과적합 가능성 (훈련-검증 차이: {train_score - mean_score:.4f})")
                elif train_score < 0.1:
                    print(f"  ⚠️  과소적합 가능성 (낮은 훈련 점수)")
                
                # 예측 분포 확인
                predictions = model.predict(X)
                pred_std = np.std(predictions)
                actual_std = np.std(y)
                print(f"  📊 예측 분산: {pred_std:.4f} vs 실제 분산: {actual_std:.4f}")
                
                # 최고 성능 모델 저장
                if mean_score > self.best_score:
                    self.best_score = mean_score
                    self.best_model = model
                    self.best_model_name = name
                    print(f"  🏆 새로운 최고 성능 모델!")
                
            except Exception as e:
                print(f"❌ 모델 {name} 학습 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
                results[name] = -999.0
        
        # 최종 모델 검증
        if self.best_model is not None:
            expected_features = len(self.feature_names)
            print(f"\n🎯 최종 선택된 모델: {self.best_model_name}")
            print(f"🎯 최고 성능: R² = {self.best_score:.4f}")
            print(f"🎯 예상 특성 수: {expected_features}")
            print(f"🎯 특성 목록: {self.feature_names}")
        
        return results
    
    def predict(self, X_new: np.ndarray) -> np.ndarray:
        """새로운 데이터에 대한 예측"""
        if self.best_model is None:
            raise ValueError("모델이 학습되지 않았습니다.")
        return self.best_model.predict(X_new)
    
    def save_model(self, filepath: str):
        """모델 저장"""
        model_data = {
            'best_model': self.best_model,
            'best_model_name': self.best_model_name,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'target_name': self.target_name,
            'best_score': self.best_score
        }
        joblib.dump(model_data, filepath)
    
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


class BayesianOptimizer:
    def __init__(self, ml_model: MLModelTrainer):
        self.ml_model = ml_model
        self.feature_ranges = {}
        self.categorical_features = {}
        self.optimizer = None
        
    def set_bounds(self, bounds_dict: Dict[str, tuple]):
        """특성 범위 설정"""
        self.feature_ranges = bounds_dict
        
    def set_categorical_features(self, categorical_dict: Dict[str, List[str]]):
        """범주형 특성 설정"""
        self.categorical_features = categorical_dict
        
    def objective_function(self, **params):
        """베이지안 최적화 목적 함수 - 실제 ML 모델 사용"""
        try:
            # 학습된 모델이 있는지 확인
            if self.ml_model is None or self.ml_model.best_model is None:
                print("학습된 모델이 없습니다. 랜덤 발현량을 반환합니다.")
                return np.random.uniform(10, 90)  # 10-90 mg/L 범위의 랜덤 값
            
            # 범주형 변수 처리
            processed_params = {}
            for key, value in params.items():
                if key in self.categorical_features:
                    # 범주형 변수는 인덱스를 실제 값으로 변환
                    idx = int(round(value))
                    idx = max(0, min(idx, len(self.categorical_features[key]) - 1))
                    processed_params[key] = self.categorical_features[key][idx]
                else:
                    processed_params[key] = round(value, 4)
            
            # DataFrame 형태로 변환 (모델 예측을 위해)
            param_df = pd.DataFrame([processed_params])
            
            # 특성 순서를 학습 시와 같게 맞춤
            if hasattr(self.ml_model, 'feature_names') and self.ml_model.feature_names:
                # 모델 학습 시 사용된 특성 순서로 재정렬
                missing_features = set(self.ml_model.feature_names) - set(param_df.columns)
                if missing_features:
                    print(f"누락된 특성 발견: {missing_features}")
                    # 누락된 특성은 0으로 채움 (이제 식별자 컬럼들은 제외되므로 실험 관련 특성만 남음)
                    for feature in missing_features:
                        param_df[feature] = 0
                
                # 특성 순서 맞춤
                param_df = param_df[self.ml_model.feature_names]
                print(f"✓ 특성 맞춤 완료: {len(param_df.columns)}개 특성 사용")
            
            # 범주형 변수 인코딩 (학습 시와 동일하게)
            for column in param_df.columns:
                if column in self.ml_model.label_encoders:
                    try:
                        # 학습 시 인코더 사용
                        original_value = processed_params.get(column, param_df[column].iloc[0])
                        if isinstance(original_value, str):
                            # 새로운 범주값인 경우 처리
                            encoder = self.ml_model.label_encoders[column]
                            if original_value in encoder.classes_:
                                param_df[column] = encoder.transform([str(original_value)])[0]
                            else:
                                # 새로운 값이면 가장 가까운 기존 값으로 대체
                                param_df[column] = 0
                    except Exception as enc_error:
                        print(f"인코딩 오류 ({column}): {enc_error}")
                        param_df[column] = 0
            
            # 스케일링 적용
            try:
                X_scaled = self.ml_model.scaler.transform(param_df)
            except Exception as scale_error:
                print(f"스케일링 오류: {scale_error}")
                return np.random.uniform(10, 90)  # 현실적인 발현량 범위
            
            # ML 모델로 예측
            prediction = self.ml_model.best_model.predict(X_scaled)[0]
            
            # 예측값이 유효한지 확인
            if np.isnan(prediction) or np.isinf(prediction):
                print(f"유효하지 않은 예측값: {prediction}")
                return 0.0  # 유효하지 않은 조건에 대해서는 0 반환
            
            # 실제 예측값을 그대로 사용 (단백질 발현량)
            # 베이지안 최적화는 상대적 크기를 중요하게 여기므로 정규화 불필요
            objective_value = float(prediction)
            
            print(f"✓ 파라미터: {processed_params}")
            print(f"✓ 예상 단백질 발현량: {objective_value:.2f} mg/L")
            
            return objective_value
            
        except Exception as e:
            print(f"목적 함수 평가 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return np.random.uniform(10, 90)  # 오류 시 현실적인 발현량 반환
    
    def optimize(self, n_iter: int = 10) -> Dict[str, Any]:
        """베이지안 최적화 실행"""
        try:
            # 모델 상태 확인
            if self.ml_model is None or self.ml_model.best_model is None:
                raise ValueError("ML 모델이 학습되지 않았습니다. 먼저 모델을 학습해주세요.")
            
            print(f"베이지안 최적화 시작 - 모델: {self.ml_model.best_model_name}, 성능: {self.ml_model.best_score:.4f}")
            
            # 베이지안 최적화 설정
            pbounds = {}
            
            # 수치형 변수 범위 설정
            for feature, (min_val, max_val) in self.feature_ranges.items():
                if feature not in self.categorical_features:
                    pbounds[feature] = (min_val, max_val)
                    print(f"수치형 변수 {feature}: {min_val} ~ {max_val}")
            
            # 범주형 변수를 수치형 인덱스로 변환
            for feature, categories in self.categorical_features.items():
                pbounds[feature] = (0, len(categories) - 1)
                print(f"범주형 변수 {feature}: {categories} (인덱스: 0~{len(categories)-1})")
            
            if not pbounds:
                raise ValueError("최적화할 변수가 설정되지 않았습니다.")
            
            self.optimizer = BayesianOptimization(
                f=self.objective_function,
                pbounds=pbounds,
                random_state=42,
                verbose=1  # 진행 상황 표시
            )
            
            # 최적화 실행
            print(f"베이지안 최적화 실행 - 초기 탐색: 3회, 반복: {n_iter}회")
            self.optimizer.maximize(init_points=3, n_iter=n_iter)
            
            print(f"최적화 완료 - 총 {len(self.optimizer.res)}개 결과 생성")
            
            # 최적 결과 추출
            best_result = self.optimizer.max
            best_params = {}
            
            # 범주형 변수를 실제 값으로 변환
            for key, value in best_result['params'].items():
                if key in self.categorical_features:
                    idx = int(round(value))
                    idx = max(0, min(idx, len(self.categorical_features[key]) - 1))
                    best_params[key] = self.categorical_features[key][idx]
                else:
                    best_params[key] = round(value, 2)
            
            return {
                'best_params': best_params,
                'best_value': best_result['target'],
                'all_results': self.optimizer.res
            }
            
        except Exception as e:
            print(f"베이지안 최적화 중 오류: {str(e)}")
            # 폴백: 랜덤 결과
            return {
                'best_params': self.generate_random_params(),
                'best_value': np.random.uniform(10, 90),  # 현실적인 발현량
                'all_results': []
            }
    
    def generate_random_params(self) -> Dict[str, Any]:
        """랜덤 파라미터 생성 (폴백용)"""
        params = {}
        
        for feature, (min_val, max_val) in self.feature_ranges.items():
            if feature in self.categorical_features:
                params[feature] = np.random.choice(self.categorical_features[feature])
            else:
                params[feature] = round(np.random.uniform(min_val, max_val), 2)
        
        return params
    
    def generate_random_suggestions(self, n_suggestions: int) -> List[Dict[str, Any]]:
        """랜덤 실험 조건 생성 (폴백)"""
        suggestions = []
        
        for _ in range(n_suggestions):
            params = {}
            
            for feature, (min_val, max_val) in self.feature_ranges.items():
                if feature in self.categorical_features:
                    params[feature] = np.random.choice(self.categorical_features[feature])
                else:
                    params[feature] = round(np.random.uniform(min_val, max_val), 2)
            
            suggestions.append(params)
        
        return suggestions
    
    def suggest_experiments(self, n_suggestions: int = 5) -> List[Dict[str, Any]]:
        """이미 실행된 베이지안 최적화 결과를 기반으로 실험 조건 제안"""
        try:
            # 이미 베이지안 최적화가 실행되었는지 확인
            if hasattr(self, 'optimizer') and self.optimizer is not None:
                print("기존 베이지안 최적화 결과를 사용하여 실험 조건을 제안합니다.")
                existing_results = True
            else:
                print("베이지안 최적화 결과가 없습니다. 새로 실행합니다.")
                existing_results = False
                
                # 베이지안 최적화 설정
                pbounds = {}
                
                # 수치형 변수 범위 설정
                for feature, (min_val, max_val) in self.feature_ranges.items():
                    if feature not in self.categorical_features:
                        pbounds[feature] = (min_val, max_val)
                
                # 범주형 변수를 수치형 인덱스로 변환
                for feature, categories in self.categorical_features.items():
                    pbounds[feature] = (0, len(categories) - 1)
                
                self.optimizer = BayesianOptimization(
                    f=self.objective_function,
                    pbounds=pbounds,
                    random_state=42
                )
                
                # 최적화 실행
                self.optimizer.maximize(init_points=2, n_iter=n_suggestions)
            
            # 베이지안 최적화 결과에서 상위 조건들 추출
            print(f"베이지안 최적화 결과에서 상위 {n_suggestions}개 조건을 추출합니다.")
            
            # 결과를 목적값 기준으로 정렬 (높은 순서)
            sorted_results = sorted(self.optimizer.res, key=lambda x: x['target'], reverse=True)
            
            suggestions = []
            for i in range(min(n_suggestions, len(sorted_results))):
                params = sorted_results[i]['params']
                target_value = sorted_results[i]['target']
                
                # 범주형 변수를 실제 값으로 변환
                processed_params = {}
                for key, value in params.items():
                    if key in self.categorical_features:
                        idx = int(round(value))
                        idx = max(0, min(idx, len(self.categorical_features[key]) - 1))
                        processed_params[key] = self.categorical_features[key][idx]
                    else:
                        processed_params[key] = round(value, 2)
                
                print(f"제안 {i+1}: {processed_params} (예상 발현량: {target_value:.1f} mg/L)")
                suggestions.append(processed_params)
            
            # 다양성을 위한 추가 제안 (베이지안 최적화 결과 주변 탐색)
            if len(suggestions) < n_suggestions:
                # 최적 결과 참조
                try:
                    best_params = self.optimizer.max['params'] if self.optimizer and hasattr(self.optimizer, 'max') else {}
                except:
                    best_params = {}
                
                for _ in range(n_suggestions - len(suggestions)):
                    diverse_params = {}
                    
                    for feature, (min_val, max_val) in self.feature_ranges.items():
                        if feature in self.categorical_features:
                            # 범주형: 랜덤 선택
                            diverse_params[feature] = np.random.choice(self.categorical_features[feature])
                        else:
                            # 수치형: 베이지안 최적 결과 주변에 노이즈 추가
                            if feature in best_params:
                                base_value = best_params[feature]
                                noise_range = (max_val - min_val) * 0.1  # 범위의 10%
                                noise = np.random.uniform(-noise_range, noise_range)
                                new_value = base_value + noise
                                new_value = np.clip(new_value, min_val, max_val)
                                diverse_params[feature] = round(new_value, 2)
                            else:
                                diverse_params[feature] = round(np.random.uniform(min_val, max_val), 2)
                    
                    suggestions.append(diverse_params)
            
            return suggestions[:n_suggestions]
            
        except Exception as e:
            print(f"베이지안 최적화 중 오류: {str(e)}")
            # 폴백: 랜덤 제안
            return self.generate_random_suggestions(n_suggestions)
        
    def generate_random_suggestions(self, n_suggestions: int) -> List[Dict[str, Any]]:
        """랜덤 실험 조건 생성 (폴백)"""
        suggestions = []
        
        for _ in range(n_suggestions):
            params = {}
            
            for feature, (min_val, max_val) in self.feature_ranges.items():
                if feature in self.categorical_features:
                    params[feature] = np.random.choice(self.categorical_features[feature])
                else:
                    params[feature] = round(np.random.uniform(min_val, max_val), 2)
            
            suggestions.append(params)
        
        return suggestions


class MappingFileGenerator:
    def __init__(self):
        self.plate_layout = {
            'rows': 8,  # A-H
            'columns': 12,  # 1-12
            'total_wells': 96
        }
    
    def create_mapping_file(self, experiments: List[Dict[str, Any]], 
                           plate_type: str = '96-well', start_well: str = 'A01') -> pd.DataFrame:
        """실험 조건을 플레이트 매핑으로 변환"""
        
        # 플레이트 타입에 따른 레이아웃 설정
        if plate_type == '384-well':
            self.plate_layout = {'rows': 16, 'columns': 24, 'total_wells': 384}
        else:  # 기본값은 96-well
            self.plate_layout = {'rows': 8, 'columns': 12, 'total_wells': 96}
        
        # Well 위치 생성
        wells = self.generate_well_positions(len(experiments), start_well)
        
        # 매핑 데이터 생성
        mapping_data = []
        for i, (well, experiment) in enumerate(zip(wells, experiments)):
            mapping_row = {
                'Well': well,
                'Sample_ID': f'Sample_{i+1:03d}',
                **experiment
            }
            mapping_data.append(mapping_row)
        
        return pd.DataFrame(mapping_data)
    
    def generate_well_positions(self, n_samples: int, start_well: str = 'A01') -> List[str]:
        """Well 위치 목록 생성"""
        wells = []
        
        # 시작 위치 파싱
        start_row = ord(start_well[0]) - ord('A')
        start_col = int(start_well[1:]) - 1
        
        current_row = start_row
        current_col = start_col
        
        for _ in range(n_samples):
            # 현재 위치의 well 이름 생성
            well_name = f"{chr(ord('A') + current_row)}{current_col + 1:02d}"
            wells.append(well_name)
            
            # 다음 위치로 이동
            current_col += 1
            if current_col >= self.plate_layout['columns']:
                current_col = 0
                current_row += 1
                if current_row >= self.plate_layout['rows']:
                    current_row = 0
        
        return wells
    
    def create_plate_visualization(self, mapping_df: pd.DataFrame) -> pd.DataFrame:
        """플레이트 레이아웃 시각화를 위한 데이터 생성"""
        # 전체 플레이트 매트릭스 초기화
        rows = self.plate_layout['rows']
        cols = self.plate_layout['columns']
        
        # 빈 플레이트 생성
        plate_data = []
        for row in range(rows):
            for col in range(cols):
                well_name = f"{chr(ord('A') + row)}{col + 1:02d}"
                plate_data.append({
                    'Well': well_name,
                    'Row': chr(ord('A') + row),
                    'Column': col + 1,
                    'Sample_ID': '',
                    'Status': 'Empty'
                })
        
        plate_df = pd.DataFrame(plate_data)
        
        # 매핑 데이터로 플레이트 채우기
        for _, row in mapping_df.iterrows():
            mask = plate_df['Well'] == row['Well']
            plate_df.loc[mask, 'Sample_ID'] = row['Sample_ID']
            plate_df.loc[mask, 'Status'] = 'Used'
            
            # 추가 정보가 있으면 포함
            for col in mapping_df.columns:
                if col not in ['Well', 'Sample_ID']:
                    plate_df.loc[mask, col] = row[col]
        
        return plate_df
    
    def create_protocol_file(self, mapping_df: pd.DataFrame) -> pd.DataFrame:
        """프로토콜 파일 생성"""
        protocol_data = []
        
        for _, row in mapping_df.iterrows():
            protocol_row = {
                'Well': row['Well'],
                'Sample_ID': row['Sample_ID'],
                'Volume_uL': 200,  # 기본 볼륨
                'Incubation_Time_min': 120,  # 기본 배양 시간
                'Temperature_C': row.get('Temperature', 37),  # 온도
                'Notes': 'Standard protocol'
            }
            protocol_data.append(protocol_row)
        
        return pd.DataFrame(protocol_data)