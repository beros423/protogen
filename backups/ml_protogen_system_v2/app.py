import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from sklearn.metrics import mean_squared_error, r2_score
from src.ml_core import MLModelTrainer
import warnings
warnings.filterwarnings('ignore')


# 워크플로우 관련 함수들 제거 - 단순한 상태 체크로 대체


def show_workflow_progress():
    """워크플로우 진행상황 표시 (간단한 체크리스트)"""
    if not st.session_state.current_project:
        return
    
    st.subheader(f"작업 진행상황")
    
    # 간단한 체크리스트 표시
    has_data = 'data' in st.session_state and st.session_state.data is not None
    has_model = 'trainer' in st.session_state and st.session_state.trainer is not None
    has_results = 'model_results' in st.session_state and st.session_state.model_results is not None
    
    col1, col2 = st.columns(2)
    
    with col1:
        if has_data:
            st.success("✓ 데이터 업로드 완료")
        else:
            st.info("○ 데이터 업로드 대기")
        
        if has_model:
            st.success("✓ 모델 학습 완료")
        else:
            st.info("○ 모델 학습 대기")
    
    with col2:
        if has_results:
            st.success("✓ 성능 평가 완료")
        else:
            st.info("○ 성능 평가 대기")
        
        if has_model and has_results:
            st.success("✓ 예측 준비 완료")
        else:
            st.info("○ 예측 기능 대기")
    
    st.markdown("---")


def show_next_step_button(current_menu):
    """다음 단계 버튼 표시 (간단한 버전)"""
    if not st.session_state.current_project:
        return
    
    # 현재 상태에 따른 다음 단계 제안
    has_data = 'data' in st.session_state and st.session_state.data is not None
    has_model = 'trainer' in st.session_state and st.session_state.trainer is not None
    
    st.markdown("---")
    
    if current_menu == "데이터 업로드" and has_data:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("다음: ML 모델 학습", type="primary", use_container_width=True, key="next_to_ml_training"):
                # 메뉴 변경 요청
                st.session_state.menu_change_request = "ML 모델 학습"
                st.rerun()
    
    elif current_menu == "ML 모델 학습" and has_model:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("다음: 예측 및 최적화", type="primary", use_container_width=True, key="next_to_prediction"):
                # 메뉴 변경 요청
                st.session_state.menu_change_request = "예측 및 최적화"
                st.rerun()


def generate_bayesian_suggestions(trainer, promoters, n_suggestions, exploration_weight=1.0):
    """베이지안 최적화를 통한 다음 실험 조건 제안"""
    import itertools
    
    # 가능한 모든 Promoter 조합 생성
    all_combinations = list(itertools.product(promoters, repeat=3))
    
    # 현재 데이터에서 이미 시도한 조합 확인
    tried_combinations = set()
    if 'data' in st.session_state:
        data = st.session_state.data
        for _, row in data.iterrows():
            combo = (row['CrtYB'], row['CrtI'], row['CrtE'])
            tried_combinations.add(combo)
    
    # 시도하지 않은 조합 필터링
    untried_combinations = [combo for combo in all_combinations if combo not in tried_combinations]
    
    if len(untried_combinations) == 0:
        # 모든 조합을 시도했다면 랜덤하게 일부 선택
        untried_combinations = list(all_combinations)
    
    # 각 조합에 대해 예측 수행
    suggestions = []
    
    for combo in untried_combinations[:min(len(untried_combinations), n_suggestions * 3)]:
        try:
            # 예측값 계산
            input_data = pd.DataFrame({
                'CrtYB': [combo[0]],
                'CrtI': [combo[1]], 
                'CrtE': [combo[2]]
            })
            
            # 전처리
            if hasattr(trainer, 'final_encoding_method') and hasattr(trainer, 'scaler') and trainer.scaler is not None:
                if trainer.final_encoding_method in ['onehot_drop', 'onehot'] and hasattr(trainer, 'encoder') and trainer.encoder is not None:
                    input_encoded_array = trainer.encoder.transform(input_data)
                    input_encoded = pd.DataFrame(input_encoded_array, columns=trainer.feature_names)
                elif trainer.final_encoding_method == 'label' and hasattr(trainer, 'encoders') and trainer.encoders:
                    input_encoded = input_data.copy()
                    for col in input_data.columns:
                        if col in trainer.encoders:
                            try:
                                input_encoded[col] = trainer.encoders[col].transform(input_data[col])
                            except ValueError:
                                # 새로운 범주값은 건너뛰기
                                continue
                else:
                    continue
                
                input_scaled = trainer.scaler.transform(input_encoded)
                
                # 예측
                prediction = trainer.best_model.predict(input_scaled)[0]
                
                # 타겟 변환 역변환
                if hasattr(trainer, 'final_target_transform'):
                    if trainer.final_target_transform == 'log':
                        prediction = np.exp(prediction) - 1
                    elif trainer.final_target_transform == 'sqrt':
                        prediction = prediction ** 2
                elif trainer.target_transform == 'log':
                    prediction = np.exp(prediction) - 1
                elif trainer.target_transform == 'sqrt':
                    prediction = prediction ** 2
                
                # 불확실성 추정 (모델 성능 기반)
                uncertainty = abs(prediction) * (1 - max(0, trainer.best_score)) * exploration_weight
                
                # 획득 함수: 예측값 + 탐색 가중치 * 불확실성
                acquisition_score = prediction + exploration_weight * uncertainty
                
                suggestions.append({
                    'CrtYB': combo[0],
                    'CrtI': combo[1],
                    'CrtE': combo[2],
                    'Predicted_Titer': round(prediction, 3),
                    'Uncertainty': round(uncertainty, 3),
                    'Acquisition_Score': round(acquisition_score, 3)
                })
                
        except Exception as e:
            # 예측 실패한 조합은 건너뛰기
            continue
    
    # 획득 점수 기준으로 정렬하여 상위 N개 선택
    suggestions.sort(key=lambda x: x['Acquisition_Score'], reverse=True)
    selected = suggestions[:n_suggestions]

    # 프로젝트 단위로 제안 저장 (파일 및 세션)
    try:
        if 'current_project' in st.session_state and st.session_state.current_project:
            save_project_data(st.session_state.current_project, 'suggestions', selected)
            st.session_state.suggestions = selected
    except Exception:
        pass

    return selected


def init_project_management():
    """프로젝트 관리 시스템 초기화"""
    # 프로젝트 디렉토리 생성
    projects_dir = Path("projects")
    projects_dir.mkdir(exist_ok=True)
    
    # 현재 프로젝트 초기화
    if 'current_project' not in st.session_state:
        st.session_state.current_project = None
    
    # 프로젝트 리스트 초기화
    if 'projects_list' not in st.session_state:
        st.session_state.projects_list = get_projects_list()
    
# 워크플로우 상태는 실시간으로 세션 상태에서 확인


def get_projects_list():
    """프로젝트 목록 조회"""
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return []
    
    projects = []
    for project_path in projects_dir.iterdir():
        if project_path.is_dir():
            projects.append(project_path.name)
    return sorted(projects)


def save_project_data(project_name, data_type, data):
    """프로젝트 데이터 저장"""
    project_dir = Path("projects") / project_name
    project_dir.mkdir(exist_ok=True)
    
    if data_type == "raw_data":
        file_path = project_dir / "raw_data.pkl"
    elif data_type == "model_results":
        file_path = project_dir / "model_results.pkl"
    elif data_type == "trainer":
        file_path = project_dir / "trainer.pkl"
    elif data_type == "suggestions":
        file_path = project_dir / "suggestions.pkl"
    elif data_type == "metadata":
        file_path = project_dir / "metadata.json"
    elif data_type == "workflow_status":
        file_path = project_dir / "workflow_status.json"
    elif data_type == "session_state":
        file_path = project_dir / "session_state.json"
    else:
        raise ValueError(f"Unknown data type: {data_type}")
    
    if data_type in ["metadata", "workflow_status", "session_state"]:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    else:
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)


def load_project_data(project_name, data_type):
    """프로젝트 데이터 로드"""
    project_dir = Path("projects") / project_name
    
    if data_type == "raw_data":
        file_path = project_dir / "raw_data.pkl"
    elif data_type == "model_results":
        file_path = project_dir / "model_results.pkl"
    elif data_type == "trainer":
        file_path = project_dir / "trainer.pkl"
    elif data_type == "suggestions":
        file_path = project_dir / "suggestions.pkl"
    elif data_type == "metadata":
        file_path = project_dir / "metadata.json"
    elif data_type == "workflow_status":
        file_path = project_dir / "workflow_status.json"
    elif data_type == "session_state":
        file_path = project_dir / "session_state.json"
    else:
        raise ValueError(f"Unknown data type: {data_type}")
    
    if not file_path.exists():
        return None
    
    try:
        if data_type in ["metadata", "workflow_status", "session_state"]:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생 ({data_type}): {e}")
        return None


def get_project_stats(project_name):
    """프로젝트 통계 정보 조회"""
    metadata = load_project_data(project_name, "metadata")
    if not metadata:
        return {"total_experiments": 0, "total_cycles": 0, "last_updated": None}
    
    return {
        "total_experiments": metadata.get("total_experiments", 0),
        "total_cycles": metadata.get("total_cycles", 0),
        "last_updated": metadata.get("last_updated", None)
    }


def update_project_metadata(project_name, data_count=None, cycle_increment=False):
    """프로젝트 메타데이터 업데이트"""
    metadata = load_project_data(project_name, "metadata") or {}
    
    if data_count is not None:
        metadata["total_experiments"] = data_count
    
    if cycle_increment:
        metadata["total_cycles"] = metadata.get("total_cycles", 0) + 1
    
    metadata["last_updated"] = datetime.now().isoformat()
    
    save_project_data(project_name, "metadata", metadata)


def save_project_session_state(project_name):
    """현재 세션 상태를 프로젝트에 저장"""
    if not project_name:
        return
    
    # 저장할 세션 상태 정보 수집
    session_data = {
        "last_saved": datetime.now().isoformat(),
        "has_data": 'data' in st.session_state and st.session_state.data is not None,
        "has_model": 'trainer' in st.session_state and st.session_state.trainer is not None,
        "has_results": 'model_results' in st.session_state and st.session_state.model_results is not None,
        "has_suggestions": 'suggestions' in st.session_state and st.session_state.suggestions is not None,
        "current_menu": st.session_state.get("main_menu", "데이터 업로드"),
        "data_info": {},
        "model_info": {},
        "results_info": {}
    }
    
    # 데이터 정보 저장
    if session_data["has_data"]:
        data = st.session_state.data
        session_data["data_info"] = {
            "shape": list(data.shape) if hasattr(data, 'shape') else None,
            "columns": list(data.columns) if hasattr(data, 'columns') else None,
            "data_types": str(data.dtypes.to_dict()) if hasattr(data, 'dtypes') else None
        }
    
    # 모델 정보 저장
    if session_data["has_model"]:
        trainer = st.session_state.trainer
        session_data["model_info"] = {
            "best_model": getattr(trainer, 'best_model', None),
            "target_transform": getattr(trainer, 'final_target_transform', None),
            "encoding_method": getattr(trainer, 'final_encoding_method', None),
            "has_preprocessor": hasattr(trainer, 'encoder') and trainer.encoder is not None
        }
    
    # 결과 정보 저장
    if session_data["has_results"]:
        results = st.session_state.model_results
        session_data["results_info"] = {
            "best_score": results.get("best_score", None),
            "best_params": results.get("best_params", None),
            "models_count": len(results.get("results", {}))
        }

    # 제안된 실험 정보 저장 (간단한 미리보기)
    if session_data.get("has_suggestions"):
        try:
            suggestions = st.session_state.get('suggestions', [])
            session_data['suggestions_preview'] = suggestions[:5]
        except Exception:
            session_data['suggestions_preview'] = []
    
    save_project_data(project_name, "session_state", session_data)


def restore_project_session_state(project_name):
    """프로젝트 세션 상태 복원"""
    if not project_name:
        return None
    
    session_data = load_project_data(project_name, "session_state")
    return session_data


def show_project_sidebar():
    """사이드바에 프로젝트 정보 및 진행상황 표시"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("프로젝트 선택")
    
    # 프로젝트 목록 업데이트
    st.session_state.projects_list = get_projects_list()
    
    # 프로젝트 선택 옵션 생성 (새 프로젝트 생성 포함)
    project_options = ["새 프로젝트 생성"] + st.session_state.projects_list
    
    # 현재 선택된 프로젝트의 인덱스 찾기
    if st.session_state.current_project and st.session_state.current_project in st.session_state.projects_list:
        current_index = st.session_state.projects_list.index(st.session_state.current_project) + 1  # +1 because of "새 프로젝트 생성"
    else:
        current_index = 0
    
    # 프로젝트 선택 박스
    selected_option = st.sidebar.selectbox(
        "프로젝트를 선택하세요",
        options=project_options,
        index=current_index,
        key="project_selector"
    )
    
    # 선택에 따른 처리
    if selected_option == "새 프로젝트 생성":
        # 메인 페이지에 프로젝트 생성 페이지 표시
        st.session_state.show_project_creation = True
        return
    elif selected_option != st.session_state.current_project:
        # 이전 프로젝트 세션 상태 저장
        if st.session_state.current_project:
            save_project_session_state(st.session_state.current_project)
        
        # 프로젝트 변경
        st.session_state.current_project = selected_option
        st.session_state.show_project_creation = False  # 프로젝트 생성 페이지 해제
        
        # 프로젝트 데이터 로드
        raw_data = load_project_data(selected_option, "raw_data")
        model_results = load_project_data(selected_option, "model_results")
        trainer = load_project_data(selected_option, "trainer")
        suggestions = load_project_data(selected_option, "suggestions")
        
        # 세션 상태 복원
        session_data = restore_project_session_state(selected_option)
        
        # 데이터 복원
        if raw_data is not None:
            st.session_state.data = raw_data
        else:
            if 'data' in st.session_state:
                del st.session_state.data
                
        if model_results is not None:
            st.session_state.model_results = model_results
        else:
            if 'model_results' in st.session_state:
                del st.session_state.model_results
                
        if trainer is not None:
            st.session_state.trainer = trainer
        else:
            if 'trainer' in st.session_state:
                del st.session_state.trainer
        
        # 이전에 생성된 제안 복원
        if suggestions is not None:
            st.session_state.suggestions = suggestions
        else:
            if 'suggestions' in st.session_state:
                del st.session_state.suggestions
        
        # 메뉴 상태 복원
        if session_data and "current_menu" in session_data:
            st.session_state.menu_change_request = session_data["current_menu"]
        
        st.sidebar.success(f"프로젝트 '{selected_option}' 로드됨")
        if session_data:
            st.sidebar.info(f"마지막 저장: {session_data.get('last_saved', 'Unknown')[:16]}")
        st.rerun()
    
    # 현재 프로젝트 정보 표시
    if st.session_state.current_project:
        st.sidebar.markdown("---")
        st.sidebar.subheader("프로젝트 정보")
        
        # 프로젝트 통계
        stats = get_project_stats(st.session_state.current_project)
        st.sidebar.write(f"**총 실험 데이터:** {stats['total_experiments']}개")
        st.sidebar.write(f"**완료된 Cycle:** {stats['total_cycles']}회")
        
        if stats['last_updated']:
            last_updated = datetime.fromisoformat(stats['last_updated'])
            st.sidebar.write(f"**마지막 업데이트:** {last_updated.strftime('%Y-%m-%d %H:%M')}")
        
        # 세션 상태 정보 표시
        session_data = restore_project_session_state(st.session_state.current_project)
        if session_data:
            st.sidebar.markdown("---")
            st.sidebar.subheader("저장된 상태")
            
            if session_data.get("has_data"):
                data_info = session_data.get("data_info", {})
                shape = data_info.get("shape")
                if shape:
                    st.sidebar.write(f"📊 데이터: {shape[0]}×{shape[1]}")
            
            if session_data.get("has_model"):
                model_info = session_data.get("model_info", {})
                best_model = model_info.get("best_model")
                if best_model:
                    st.sidebar.write(f"🤖 모델: {best_model}")
            
            if session_data.get("has_results"):
                results_info = session_data.get("results_info", {})
                best_score = results_info.get("best_score")
                if best_score:
                    st.sidebar.write(f"📈 점수: {best_score:.4f}")

            if session_data.get("has_suggestions"):
                previews = session_data.get('suggestions_preview', [])
                st.sidebar.write(f"💡 저장된 제안: {len(previews)}개 (최근 {len(previews)}개 미리보기)")
            
            # 마지막 메뉴 위치
            last_menu = session_data.get("current_menu", "데이터 업로드")
            st.sidebar.write(f"📍 마지막 위치: {last_menu}")
        
        # 진행상황 표시
        if stats['total_cycles'] > 0:
            progress_text = f"Cycle {stats['total_cycles']} 완료"
            st.sidebar.success(progress_text)
        else:
            st.sidebar.info("학습 대기 중")


def show_new_project_creation():
    """메인 페이지에서 새 프로젝트 생성"""
    st.header("새 프로젝트 생성")
    
    st.markdown("""
    새로운 베타카로틴 생산 최적화 프로젝트를 생성합니다.
    각 실험 시리즈별로 별도의 프로젝트를 생성하는 것을 권장합니다.
    """)
    
    # 기존 프로젝트 목록 표시
    st.session_state.projects_list = get_projects_list()
    if st.session_state.projects_list:
        st.subheader("기존 프로젝트")
        
        # 프로젝트 카드 형태로 표시
        cols = st.columns(3)
        for i, project_name in enumerate(st.session_state.projects_list):
            col_idx = i % 3
            with cols[col_idx]:
                stats = get_project_stats(project_name)
                with st.container():
                    st.markdown(f"**{project_name}**")
                    st.write(f"📊 데이터: {stats['total_experiments']}개")
                    st.write(f"🔄 Cycle: {stats['total_cycles']}회")
                    if st.button(f"선택", key=f"select_{project_name}"):
                        st.session_state.current_project = project_name
                        st.session_state.show_project_creation = False  # 프로젝트 생성 페이지 해제
                        st.session_state.menu_change_request = "데이터 업로드"
                        st.rerun()
        
        st.markdown("---")
    
    # 새 프로젝트 생성 폼
    st.subheader("새 프로젝트 정보")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("new_project_form"):
            new_project_name = st.text_input(
                "프로젝트 이름",
                placeholder="예: beta_carotene_exp_1",
                help="영문, 숫자, 언더스코어(_)만 사용 가능합니다."
            )
            
            project_description = st.text_area(
                "프로젝트 설명 (선택사항)",
                placeholder="실험 목적, 조건, 특이사항 등을 입력하세요",
                height=100
            )
            
            submitted = st.form_submit_button("프로젝트 생성", type="primary", use_container_width=True)
            
            if submitted:
                if new_project_name and new_project_name not in st.session_state.projects_list:
                    # 프로젝트 디렉토리 생성
                    project_dir = Path("projects") / new_project_name
                    project_dir.mkdir(exist_ok=True)
                    
                    # 초기 메타데이터 저장
                    metadata = {
                        "name": new_project_name,
                        "description": project_description,
                        "created_at": datetime.now().isoformat(),
                        "total_experiments": 0,
                        "total_cycles": 0
                    }
                    save_project_data(new_project_name, "metadata", metadata)
                    
                    # 프로젝트 선택 후 데이터 업로드 페이지로 이동
                    st.session_state.current_project = new_project_name
                    st.session_state.projects_list = get_projects_list()
                    st.session_state.show_project_creation = False  # 프로젝트 생성 페이지 해제
                    st.session_state.menu_change_request = "데이터 업로드"
                    
                    st.success(f"프로젝트 '{new_project_name}' 생성 완료!")
                    st.info("데이터 업로드 페이지로 이동합니다...")
                    st.rerun()
                elif new_project_name in st.session_state.projects_list:
                    st.error("이미 존재하는 프로젝트 이름입니다.")
                else:
                    st.error("프로젝트 이름을 입력해주세요.")
    
    with col2:
        st.info("""
        **프로젝트 네이밍 권장사항**
        
        • **실험 날짜**: exp_2024_10_14
        • **조건별**: high_temp_condition  
        • **시리즈별**: series_001, series_002
        • **목적별**: optimization_v1
        
        **주의사항**
        • 한글, 공백, 특수문자 피하기
        • 짧고 명확한 이름 사용
        • 나중에 구분하기 쉬운 이름
        """)





def main():
    st.set_page_config(
        page_title="Protogen ML 실험 최적화 시스템",
        page_icon="",
        layout="wide"
    )
    
    st.title("Protogen: ML 실험 최적화 및 모델 학습")
    st.markdown("---")
    
    # 프로젝트 관리 초기화
    init_project_management()
    
    # 사이드바 프로젝트 정보 및 진행상황
    show_project_sidebar()
    
    # 워크플로우 진행상황 표시
    if st.session_state.current_project:
        show_workflow_progress_sidebar()
    
    # 사이드바: 주요 작업을 버튼으로 선택하도록 변경
    sidebar_pages = [
        ("데이터 준비", "데이터 준비"),
        ("초기 모델 학습", "초기 모델 학습"),
        ("학습 결과 및 추가 데이터 제시", "학습 결과 및 추가 데이터 제시"),
        ("데이터 입력 및 추가학습", "데이터 입력 및 추가학습"),
        ("프로젝트 관리", "프로젝트 관리"),
        ("도움말", "도움말"),
        ("홈", "홈")
    ]

    # 메뉴 변경 요청 처리
    if 'menu_change_request' in st.session_state:
        st.session_state.main_menu = st.session_state.menu_change_request
        del st.session_state.menu_change_request

    if 'main_menu' not in st.session_state:
        st.session_state.main_menu = '홈'

    st.sidebar.markdown("---")
    st.sidebar.subheader("작업 선택")
    for label, key in sidebar_pages:
        if st.sidebar.button(label, key=f"btn_{key}"):
            st.session_state.main_menu = key
            st.rerun()

    menu = st.session_state.get('main_menu', '홈')
    
    # 프로젝트 생성 페이지 표시 확인
    if st.session_state.get('show_project_creation', False):
        show_new_project_creation()
    elif menu == "데이터 준비":
        show_data_upload()
    elif menu == "초기 모델 학습":
        show_ml_training()
    elif menu == "학습 결과 및 추가 데이터 제시":
        # 학습 결과를 먼저 보여주고 추가 데이터/제안도 함께 표시
        if 'model_results' in st.session_state and 'trainer' in st.session_state:
            show_training_results(st.session_state.model_results, st.session_state.trainer)
            show_prediction()
        else:
            st.info("먼저 모델을 학습해주세요 (초기 모델 학습).")
    elif menu == "데이터 입력 및 추가학습":
        # 추가 데이터 업로드 및 재학습 유도
        show_prediction()
    elif menu == "프로젝트 관리":
        show_project_management()
    elif menu == "도움말":
        show_help()
    else:
        show_home()
    
    # 세션 종료 시 현재 프로젝트 상태 저장
    if st.session_state.current_project:
        save_project_session_state(st.session_state.current_project)


def show_project_management():
    """프로젝트 관리 페이지"""
    st.header("프로젝트 관리")
    
    if not st.session_state.current_project:
        st.info("사이드바에서 프로젝트를 선택하거나 새로 생성하세요.")
        st.markdown("---")
    
    # 프로젝트 목록 새로고침
    st.session_state.projects_list = get_projects_list()
    
    if st.session_state.projects_list:
        st.subheader("전체 프로젝트 현황")
        
        # 프로젝트별 통계 테이블
        project_stats = []
        for project_name in st.session_state.projects_list:
            stats = get_project_stats(project_name)
            metadata = load_project_data(project_name, "metadata")
            
            project_stats.append({
                "프로젝트명": project_name,
                "생성일": metadata.get("created_at", "Unknown")[:10] if metadata else "Unknown",
                "실험 데이터": f"{stats['total_experiments']}개",
                "완료 Cycle": f"{stats['total_cycles']}회",
                "마지막 업데이트": stats['last_updated'][:10] if stats['last_updated'] else "None",
                "현재 선택": "✓" if project_name == st.session_state.current_project else ""
            })
        
        df_stats = pd.DataFrame(project_stats)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
        
        # 프로젝트 삭제 기능
        st.markdown("---")
        st.subheader("프로젝트 삭제")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            project_to_delete = st.selectbox(
                "삭제할 프로젝트를 선택하세요",
                options=st.session_state.projects_list,
                index=None,
                help="주의: 삭제된 프로젝트는 복구할 수 없습니다."
            )
        
        with col2:
            if project_to_delete:
                if st.button("프로젝트 삭제", type="secondary"):
                    if delete_project(project_to_delete):
                        if st.session_state.current_project == project_to_delete:
                            st.session_state.current_project = None
                            # 세션 데이터 정리
                            for key in ['data', 'model_results', 'trainer', 'best_score', 'best_model_name']:
                                if key in st.session_state:
                                    del st.session_state[key]
                        
                        st.session_state.projects_list = get_projects_list()
                        st.success(f"프로젝트 '{project_to_delete}'가 삭제되었습니다.")
                        st.rerun()
            else:
                st.error("프로젝트 삭제 중 오류가 발생했습니다.")
    else:
        st.info("생성된 프로젝트가 없습니다. 사이드바에서 새 프로젝트를 생성하세요.")
    
    # 홈 화면에서는 다음 단계 버튼 제거
def delete_project(project_name):
    """프로젝트 삭제"""
    try:
        import shutil
        project_dir = Path("projects") / project_name
        if project_dir.exists():
            shutil.rmtree(project_dir)
        return True
    except Exception as e:
        print(f"프로젝트 삭제 오류: {str(e)}")
        return False


def show_workflow_progress_sidebar():
    """사이드바에 간단한 진행상황 표시"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("작업 현황")
    
    # 간단한 상태 체크
    has_data = 'data' in st.session_state and st.session_state.data is not None
    has_model = 'trainer' in st.session_state and st.session_state.trainer is not None
    has_results = 'model_results' in st.session_state and st.session_state.model_results is not None
    
    if has_data:
        st.sidebar.success("✓ 데이터 준비")
    else:
        st.sidebar.info("○ 데이터 준비")
    
    if has_model:
        st.sidebar.success("✓ 모델 학습")
    else:
        st.sidebar.info("○ 모델 학습")
    
    if has_results:
        st.sidebar.success("✓ 성능 평가")
    else:
        st.sidebar.info("○ 성능 평가")
    
    if has_model and has_results:
        st.sidebar.success("✓ 예측 준비")
    else:
        st.sidebar.info("○ 예측 준비")


def show_home():
    """홈 페이지"""
    st.header("베타카로틴 생산 최적화 시스템")
    
    # 워크플로우 진행상황 표시
    if st.session_state.current_project:
        show_workflow_progress()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 시스템 개요
        
        이 시스템은 베타카로틴 생산 최적화를 위한 **기계학습 기반 단백질 발현 시스템**입니다.
        
        #### 주요 기능
        
        **1. 데이터 처리**
        - 자동 데이터 전처리 및 품질 검증
        - One-Hot 인코딩으로 Promoter 독립 효과 분석
        - Log 변환을 통한 타겟 변수 정규화
        
        **2. ML 모델링**
        - 선형 모델 중심 (Ridge, Lasso, ElasticNet, Polynomial)
        - 자동 특성 선택 및 정규화
        - 교차 검증 기반 성능 평가
        
        **3. 실험 최적화**
        - 베이지안 최적화를 통한 실험 설계
        - OT-2 로봇용 매핑 파일 자동 생성
        - 실시간 성능 모니터링
        """)
    
    with col2:
        if st.session_state.current_project:
            # 현재 상태에 따른 다음 단계 안내
            has_data = 'data' in st.session_state and st.session_state.data is not None
            has_model = 'trainer' in st.session_state and st.session_state.trainer is not None
            has_results = 'model_results' in st.session_state and st.session_state.model_results is not None
            
            if not has_data:
                st.warning("**다음 단계: 데이터 업로드**")
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.info("실험 데이터를 업로드하여 시작하세요.")
                with col_b:
                    if st.button("데이터 업로드", type="primary", key="home_to_upload"):
                        st.session_state.menu_change_request = "데이터 업로드"
                        st.rerun()
            elif not has_model or not has_results:
                st.warning("**다음 단계: ML 모델 학습**")
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.info("데이터가 준비되었습니다. 모델을 학습하세요.")
                with col_b:
                    if st.button("모델 학습", type="primary", key="home_to_training"):
                        st.session_state.menu_change_request = "ML 모델 학습"
                        st.rerun()
            else:
                st.success("**준비 완료: 예측 및 최적화**")
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.info("모든 준비가 완료되었습니다. 최적 조건을 탐색하세요.")
                with col_b:
                    if st.button("예측 시작", type="primary", key="home_to_prediction"):
                        st.session_state.menu_change_request = "예측 및 최적화"
                        st.rerun()
                
            st.markdown("---")
            st.info("""
            **권장 데이터 형식**
            - CrtYB, CrtI, CrtE: Promoter 정보
            - avg: 베타카로틴 titer (타겟)
            """)
        else:
            st.warning("**프로젝트를 선택하거나 생성하세요**")
            
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.info("베타카로틴 생산 최적화를 시작하려면 먼저 프로젝트를 생성하세요.")
            with col_b:
                if st.button("새 프로젝트 생성", type="primary", key="home_to_new_project"):
                    st.session_state.menu_change_request = "새 프로젝트 생성"
                    st.rerun()
            
            st.markdown("---")
            st.info("""
            **시작하기**
            
            1. **프로젝트 생성**: 새로운 실험 프로젝트 생성
            2. **데이터 업로드**: 베타카로틴 실험 데이터 (.xlsx, .csv)
            3. **ML 모델 학습**: 자동 전처리 및 모델 학습
            4. **예측 및 최적화**: 최적 조건 탐색 및 다음 실험 설계
            
            **프로젝트 상태 관리**
            - 🔄 **자동 저장**: 작업 완료 시 진행상황 자동 저장
            - 📂 **프로젝트 전환**: 다른 프로젝트로 전환 시 현재 상태 보존
            - 🔄 **상태 복원**: 프로젝트 로드 시 마지막 작업 상태 자동 복원
            
            **권장 데이터 형식**
            - CrtYB, CrtI, CrtE: Promoter 정보
            - avg: 베타카로틴 titer (타겟)
            """)
        
        # 현재 프로젝트 정보
        if st.session_state.current_project:
            st.success(f"현재 프로젝트: {st.session_state.current_project}")
            
            # 프로젝트 통계
            stats = get_project_stats(st.session_state.current_project)
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric("실험 데이터", f"{stats['total_experiments']}개")
            
            with col_b:
                st.metric("완료 Cycle", f"{stats['total_cycles']}회")
            
            if 'model_results' in st.session_state:
                best_score = st.session_state.get('best_score', 0)
                st.metric("최고 R² 점수", f"{best_score:.4f}")
        else:
            st.warning("왼쪽 사이드바에서 프로젝트를 선택하거나 생성해주세요")


def show_data_upload():
    """데이터 업로드 페이지"""
    st.header("데이터 업로드")
    
    # 프로젝트 선택 확인
    if not st.session_state.current_project:
        st.warning("먼저 사이드바에서 프로젝트를 선택하거나 생성해주세요.")
        st.info("사이드바에서 '새 프로젝트'를 클릭하거나 기존 프로젝트를 선택하세요.")
        return
    
    st.info(f"현재 프로젝트: **{st.session_state.current_project}**")
    
    uploaded_file = st.file_uploader(
        "베타카로틴 실험 데이터를 업로드하세요",
        type=['xlsx', 'csv'],
        help="Excel (.xlsx) 또는 CSV (.csv) 파일을 지원합니다"
    )
    
    if uploaded_file is not None:
        try:
            # 파일 로드
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            st.session_state.data = df
            
            # 프로젝트에 데이터 저장
            save_project_data(st.session_state.current_project, "raw_data", df)
            update_project_metadata(st.session_state.current_project, data_count=len(df))
            
            # 세션 상태 저장
            save_project_session_state(st.session_state.current_project)
            
# 데이터 업로드 완료
            
            st.success(f"데이터가 성공적으로 로드되었습니다! 크기: {df.shape}")
            
            # 데이터 미리보기
            st.subheader("데이터 미리보기")
            st.dataframe(df.head(10), use_container_width=True)
            
            # 데이터 요약 정보
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("기본 정보")
                st.write(f"- **행 수**: {len(df):,}")
                st.write(f"- **컬럼 수**: {len(df.columns)}")
                st.write(f"- **결측값**: {df.isnull().sum().sum()}")
                
                # 컬럼 타입 분석
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
                
                st.write(f"- **범주형 컬럼**: {len(categorical_cols)}개")
                st.write(f"- **수치형 컬럼**: {len(numerical_cols)}개")
            
            with col2:
                st.subheader("컬럼 정보")
                
                # 컬럼별 세부 정보
                for col in df.columns:
                    if df[col].dtype == 'object':
                        unique_count = df[col].nunique()
                        st.write(f"**{col}**: 범주형 ({unique_count}개 고유값)")
                    else:
                        min_val, max_val = df[col].min(), df[col].max()
                        st.write(f"**{col}**: 수치형 ({min_val:.3f} ~ {max_val:.3f})")
            
            # 데이터 품질 검사
            st.subheader("데이터 품질 검사")
            
            quality_issues = []
            
            # 1. 결측값 검사
            missing_cols = df.columns[df.isnull().any()].tolist()
            if missing_cols:
                quality_issues.append(f"결측값이 있는 컬럼: {missing_cols}")
            
            # 2. 중복 행 검사
            duplicates = df.duplicated().sum()
            if duplicates > 0:
                quality_issues.append(f"중복된 행: {duplicates}개")
            
            # 3. 베타카로틴 특화 검사
            expected_cols = ['CrtYB', 'CrtI', 'CrtE', 'avg']
            missing_expected = [col for col in expected_cols if col not in df.columns]
            if missing_expected:
                quality_issues.append(f"예상 컬럼 누락: {missing_expected}")
            
            if quality_issues:
                st.warning("발견된 데이터 품질 이슈:")
                for issue in quality_issues:
                    st.write(f"  - {issue}")
            else:
                st.success("데이터 품질이 양호합니다!")
            
        except Exception as e:
            st.error(f"파일 로드 중 오류가 발생했습니다: {str(e)}")
    
    # 다음 단계 버튼 표시
    show_next_step_button("데이터 업로드")


def show_ml_training():
    """ML 모델 학습 페이지"""
    st.header("ML 모델 학습")
    
    # 프로젝트 확인
    if not st.session_state.current_project:
        st.warning("먼저 프로젝트를 선택하거나 생성해주세요.")
        return
    
    # 데이터 확인
    if 'data' not in st.session_state:
        st.warning("먼저 데이터를 업로드해주세요!")
        st.info("사이드바에서 '데이터 업로드' 메뉴를 선택하세요.")
        return
    
    df = st.session_state.data
    
    st.info(f"현재 프로젝트: **{st.session_state.current_project}**")
    
    # 모델 및 전처리 설정
    st.subheader("모델 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**모델 선택 전략:**")
        model_strategy = st.selectbox(
            "모델 전략을 선택하세요",
            options=['linear_focused', 'ensemble_focused', 'all'],
            format_func=lambda x: {
                'linear_focused': '선형 모델 중심 (권장)',
                'ensemble_focused': '앙상블 모델 중심', 
                'all': '모든 모델 비교'
            }[x],
            index=0,
            help="베타카로틴 데이터의 특성상 선형 모델 중심을 권장합니다"
        )
    
    with col2:
        st.write("**범주형 데이터 인코딩:**")
        encoding_method = st.selectbox(
            "인코딩 방법을 선택하세요",
            options=['auto', 'onehot_drop', 'label'],
            format_func=lambda x: {
                'auto': '자동 선택 (One-Hot 우선)',
                'onehot_drop': 'One-Hot (다중공선성 방지)',
                'label': 'Label Encoding'
            }[x],
            index=0,
            help="Promoter는 명목형 데이터이므로 One-Hot 인코딩이 적합합니다"
        )
    
    # 타겟 변수 변환
    st.write("**타겟 변수 변환:**")
    target_transform = st.selectbox(
        "타겟 변수 변환 방법을 선택하세요",
        options=['auto', 'log', 'sqrt', 'none'],
        format_func=lambda x: {
            'auto': '자동 선택 (분포 분석 기반)',
            'log': 'Log 변환 (왜도 개선)',
            'sqrt': 'Square Root 변환',
            'none': '변환 없음'
        }[x],
        index=0,
        help="왜도가 높은 베타카로틴 데이터는 Log 변환이 효과적입니다"
    )
    
    # 특성 및 타겟 선택
    st.subheader("특성 및 타겟 변수 선택")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**특성 변수 선택:**")
        available_features = df.columns.tolist()
        feature_columns = st.multiselect(
            "특성으로 사용할 컬럼을 선택하세요",
            options=available_features,
            default=['CrtYB', 'CrtI', 'CrtE'] if all(col in available_features for col in ['CrtYB', 'CrtI', 'CrtE']) else [],
            help="베타카로틴 실험의 주요 특성: CrtYB, CrtI, CrtE"
        )
    
    with col2:
        st.write("**타겟 변수 선택:**")
        target_column = st.selectbox(
            "예측하고자 하는 타겟 변수를 선택하세요",
            options=available_features,
            index=available_features.index('avg') if 'avg' in available_features else 0,
            help="일반적으로 'avg' 컬럼이 베타카로틴 titer입니다"
        )
    
    # 학습 실행
    if st.button("모델 학습 시작", type="primary"):
        if not feature_columns:
            st.error("특성 변수를 최소 1개 이상 선택해주세요!")
            return
        
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 1. 모델 초기화
            status_text.text("모델 초기화 중...")
            progress_bar.progress(20)
            
            trainer = MLModelTrainer(
                model_preference=model_strategy,
                encoding_method=encoding_method,
                target_transform=target_transform
            )
            
            # 2. 데이터 전처리
            status_text.text("데이터 전처리 중...")
            progress_bar.progress(40)
            
            with st.expander("전처리 로그", expanded=True):
                import sys
                from io import StringIO
                
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()
                
                try:
                    X, y = trainer.preprocess_data(df, target_column, feature_columns)
                    output = captured_output.getvalue()
                finally:
                    sys.stdout = old_stdout
                
                st.code(output)
            
            # 3. 모델 학습
            status_text.text("모델 학습 중...")
            progress_bar.progress(70)
            
            with st.expander("학습 로그", expanded=True):
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()
                
                try:
                    results = trainer.train_models(X, y)
                    output = captured_output.getvalue()
                finally:
                    sys.stdout = old_stdout
                
                st.code(output)
            
            # 4. 결과 저장
            status_text.text("결과 저장 중...")
            progress_bar.progress(90)
            
            # 세션에 결과 저장
            st.session_state.trainer = trainer
            st.session_state.model_results = results
            st.session_state.best_score = trainer.best_score
            st.session_state.best_model_name = trainer.best_model_name
            # 전처리된 데이터 저장 (시각화 및 재예측에 사용)
            try:
                st.session_state.preprocessed = {
                    'X': X,
                    'y': y,
                    'X_raw': df[feature_columns] if feature_columns else None
                }
            except Exception:
                st.session_state.preprocessed = None
            
            # 프로젝트에 저장
            save_project_data(st.session_state.current_project, "trainer", trainer)
            save_project_data(st.session_state.current_project, "model_results", results)
            update_project_metadata(st.session_state.current_project, cycle_increment=True)
            
            # 세션 상태 저장
            save_project_session_state(st.session_state.current_project)
            
# 모델 학습 완료
            
            progress_bar.progress(100)
            status_text.text("학습 완료!")
            
            # 결과 표시
            st.success("모델 학습이 완료되었습니다!")
            
            # 성능 결과 표시
            show_training_results(results, trainer)
            
        except Exception as e:
            st.error(f"학습 중 오류가 발생했습니다: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    # 다음 단계 버튼 표시
    show_next_step_button("ML 모델 학습")


def show_training_results(results, trainer):
    """학습 결과 표시"""
    st.subheader("학습 결과")
    
    # 성능 비교 차트
    results_df = pd.DataFrame(list(results.items()), columns=['Model', 'R² Score'])
    results_df = results_df[results_df['R² Score'] > -100]  # 오류 제외
    results_df = results_df.sort_values('R² Score', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 막대 차트
        fig = px.bar(
            results_df, 
            x='Model', 
            y='R² Score',
            title="모델 성능 비교 (R² Score)",
            color='R² Score',
            color_continuous_scale='RdYlGn'
        )
        fig.add_hline(y=0, line_dash="dash", line_color="red", 
                     annotation_text="베이스라인 (R²=0)")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 메트릭 표시
        st.metric("최고 성능 모델", trainer.best_model_name or "None")
        st.metric("최고 R² 점수", f"{trainer.best_score:.4f}")
        
        # 성능 해석
        if trainer.best_score < 0:
            st.error("성능이 베이스라인보다 낮습니다")
        elif trainer.best_score < 0.3:
            st.warning("성능 개선이 필요합니다")
        elif trainer.best_score < 0.7:
            st.info("보통 수준의 성능입니다")
        else:
            st.success("우수한 성능입니다!")
    
    # 추가 시각화: 데이터 트렌드 및 예측 vs 실제
    try:
        if 'trainer' in st.session_state and st.session_state.trainer is not None and 'data' in st.session_state:
            trainer_obj = st.session_state.trainer
            data_df = st.session_state.data.copy()

            # 트렌드: 타겟 변수의 전체 경향성
            target_col = getattr(trainer_obj, 'target_name', None) or 'avg'
            if target_col in data_df.columns:
                trend_fig = px.line(
                    data_df.reset_index().rename(columns={'index': 'idx'}),
                    x='idx', y=target_col,
                    title='전체 실험 데이터의 타겟 경향성',
                    markers=True
                )
                trend_fig.update_layout(xaxis_title='실험 인덱스', yaxis_title=target_col)
            else:
                trend_fig = None

            # 예측 vs 실제
            preds_fig = None
            try:
                if 'preprocessed' in st.session_state and st.session_state.preprocessed:
                    X_scaled = st.session_state.preprocessed['X']
                    # trainer.predict will handle inverse transform
                    preds = trainer_obj.predict(X_scaled)
                    # 원래 실제값
                    if trainer_obj.target_name and trainer_obj.target_name in data_df.columns:
                        actuals = data_df[trainer_obj.target_name].values
                    else:
                        actuals = None
                else:
                    # 재전처리 시도 (주의: 인코더/스케일러가 trainer에 저장되어 있어야 함)
                    if trainer_obj.feature_names:
                        X_tmp, y_tmp = trainer_obj.preprocess_data(data_df, trainer_obj.target_name, trainer_obj.feature_names)
                        preds = trainer_obj.predict(X_tmp)
                        actuals = data_df[trainer_obj.target_name].values if trainer_obj.target_name in data_df.columns else None
                    else:
                        preds = None
                        actuals = None

                if preds is not None and actuals is not None and len(preds) == len(actuals):
                    df_pa = pd.DataFrame({'Actual': actuals, 'Predicted': preds})
                    preds_fig = px.scatter(df_pa, x='Actual', y='Predicted', trendline='ols',
                                           title='예측 vs 실제 (전체 데이터)')
                    preds_fig.add_shape(type='line', x0=df_pa['Actual'].min(), x1=df_pa['Actual'].max(),
                                        y0=df_pa['Actual'].min(), y1=df_pa['Actual'].max(), line=dict(dash='dash', color='red'))
                    preds_fig.update_layout(xaxis_title='실제', yaxis_title='예측')
            except Exception:
                preds_fig = None

            if trend_fig or preds_fig:
                st.markdown("---")
                st.subheader("데이터 시각화")
                viz_cols = st.columns(2)
                with viz_cols[0]:
                    if trend_fig:
                        st.plotly_chart(trend_fig, use_container_width=True)
                with viz_cols[1]:
                    if preds_fig:
                        st.plotly_chart(preds_fig, use_container_width=True)
    except Exception:
        pass

    # 상세 결과 테이블
    st.dataframe(results_df, use_container_width=True)
    
    # 선형 모델 계수 해석
    if (trainer.best_model_name and 
        any(model_type in trainer.best_model_name.lower() 
            for model_type in ['linear', 'ridge', 'lasso', 'elastic'])):
        
        show_linear_model_interpretation(trainer)


def show_linear_model_interpretation(trainer):
    """선형 모델 계수 해석"""
    st.subheader("선형 모델 계수 해석")
    
    try:
        if hasattr(trainer.best_model, 'coef_'):
            coefficients = trainer.best_model.coef_
            intercept = getattr(trainer.best_model, 'intercept_', 0)
            
            # 계수 DataFrame 생성
            coef_df = pd.DataFrame({
                'Feature': trainer.feature_names,
                'Coefficient': coefficients,
                'Abs_Coefficient': np.abs(coefficients)
            }).sort_values('Abs_Coefficient', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 계수 중요도 차트
                fig = px.bar(
                    coef_df, 
                    x='Feature', 
                    y='Coefficient',
                    title="특성별 회귀 계수",
                    color='Coefficient',
                    color_continuous_scale='RdBu_r'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.write("**계수 해석:**")
                st.write(f"절편: {intercept:.4f}")
                st.write("**중요 특성 Top 3:**")
                for i, (_, row) in enumerate(coef_df.head(3).iterrows()):
                    direction = "양의 영향" if row['Coefficient'] > 0 else "음의 영향"
                    st.write(f"{i+1}. {row['Feature']}: {direction}")
            
            # 계수 테이블
            st.write("**전체 계수:**")
            display_coef = coef_df[['Feature', 'Coefficient']].copy()
            display_coef['Coefficient'] = display_coef['Coefficient'].round(4)
            st.dataframe(display_coef, use_container_width=True, hide_index=True)
            
        else:
            st.info("선택된 모델은 계수 해석이 불가능합니다.")
            
    except Exception as e:
        st.warning(f"계수 해석 중 오류: {str(e)}")


def show_prediction():
    """예측 및 최적화 페이지"""
    st.header("예측 및 최적화")
    
    if not st.session_state.current_project:
        st.warning("먼저 프로젝트를 선택하거나 생성해주세요.")
        return
    
    if 'trainer' not in st.session_state:
        st.warning("먼저 모델을 학습해주세요!")
        st.info("사이드바에서 'ML 모델 학습' 메뉴를 선택하세요.")
        return
    
    trainer = st.session_state.trainer
    
    st.info(f"현재 프로젝트: **{st.session_state.current_project}**")
    # 이전에 생성된 제안이 있으면 먼저 표시
    if 'suggestions' in st.session_state and st.session_state.suggestions:
        st.subheader("저장된 제안된 실험 조건")
        try:
            sug_df = pd.DataFrame(st.session_state.suggestions)
            st.dataframe(sug_df, use_container_width=True)
            csv = sug_df.to_csv(encoding='utf-8-sig')
            st.download_button(
                label="저장된 제안 CSV 다운로드",
                data=csv,
                file_name=f"saved_suggestions_{st.session_state.current_project}.csv",
                mime="text/csv"
            )
        except Exception:
            pass
        st.markdown("---")
    st.subheader("단일 조건 예측")
    
    # 특성값 입력
    st.write("**Promoter 조합을 선택하세요:**")
    
    col1, col2, col3 = st.columns(3)
    
    # CrtYB, CrtI, CrtE의 가능한 값들 (일반적인 promoter)
    promoters = ['(P) TDH3', '(P) PGK1', '(P) HHF1', '(P) ALD6', '(P) RNR1', '(P) RNR2']
    
    with col1:
        crtYB = st.selectbox("CrtYB Promoter", options=promoters, index=0)
    
    with col2:
        crtI = st.selectbox("CrtI Promoter", options=promoters, index=1)
    
    with col3:
        crtE = st.selectbox("CrtE Promoter", options=promoters, index=2)
    
    # 예측 실행
    if st.button("베타카로틴 titer 예측", type="primary"):
        try:
            # 입력 데이터 생성
            input_data = pd.DataFrame({
                'CrtYB': [crtYB],
                'CrtI': [crtI], 
                'CrtE': [crtE]
            })
            
            # 학습된 전처리기로 변환
            if hasattr(trainer, 'final_encoding_method') and hasattr(trainer, 'scaler') and trainer.scaler is not None:
                # 범주형 인코딩
                if trainer.final_encoding_method in ['onehot_drop', 'onehot'] and hasattr(trainer, 'encoder') and trainer.encoder is not None:
                    input_encoded_array = trainer.encoder.transform(input_data)
                    input_encoded = pd.DataFrame(input_encoded_array, columns=trainer.feature_names)
                elif trainer.final_encoding_method == 'label' and hasattr(trainer, 'encoders') and trainer.encoders:
                    input_encoded = input_data.copy()
                    for col in input_data.columns:
                        if col in trainer.encoders:
                            try:
                                input_encoded[col] = trainer.encoders[col].transform(input_data[col])
                            except ValueError as e:
                                st.error(f"인코딩 오류 ({col}): {str(e)}")
                                st.error("새로운 범주값이 포함되어 있습니다. 해당 값으로 모델을 재학습해주세요.")
                                return
                else:
                    st.error("인코더가 없습니다. 모델을 다시 학습해주세요.")
                    return
                
                # 수치형 스케일링
                input_scaled = trainer.scaler.transform(input_encoded)
                
                # 예측
                prediction = trainer.best_model.predict(input_scaled)[0]
                
                # 타겟 변환 역변환
                if hasattr(trainer, 'final_target_transform'):
                    if trainer.final_target_transform == 'log':
                        prediction = np.exp(prediction) - 1
                    elif trainer.final_target_transform == 'sqrt':
                        prediction = prediction ** 2
                elif trainer.target_transform == 'log':
                    prediction = np.exp(prediction) - 1
                elif trainer.target_transform == 'sqrt':
                    prediction = prediction ** 2
                
                st.success(f"예측된 베타카로틴 titer: **{prediction:.2f}**")
                
                # 신뢰구간 추정 (단순 근사)
                if hasattr(trainer, 'best_score') and trainer.best_score > 0:
                    # R²를 기반으로 대략적인 불확실성 추정
                    uncertainty = prediction * (1 - trainer.best_score) * 0.5
                    st.info(f"추정 신뢰구간: {prediction-uncertainty:.2f} ~ {prediction+uncertainty:.2f}")
                
# 예측 완료
                
            else:
                st.error("모델의 전처리기가 없습니다. 모델을 다시 학습해주세요.")
                st.info("가능한 원인:")
                st.info("- 모델이 학습되지 않았음")
                st.info("- 이전 버전으로 학습된 모델 (전처리기 정보 없음)")
                st.info("- 전처리 과정에서 오류 발생")
            
        except Exception as e:
            st.error(f"예측 중 오류: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # 베이지안 최적화 섹션
    st.subheader("베이지안 최적화 - 차기 실험 설계")
    
    st.write("""
    **베이지안 최적화**를 통해 다음 실험에서 시도할 최적의 Promoter 조합을 제안합니다.
    현재 학습된 모델을 기반으로 가장 유망한 조건들을 탐색합니다.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        n_suggestions = st.slider(
            "제안할 실험 조건 수",
            min_value=1, max_value=10, value=5,
            help="다음 실험에서 시도할 조건의 개수"
        )
        
        exploration_weight = st.slider(
            "탐색 가중치",
            min_value=0.0, max_value=2.0, value=1.0, step=0.1,
            help="높을수록 새로운 영역 탐색, 낮을수록 확실한 영역 활용"
        )
    
    with col2:
        st.write("**현재 모델 성능:**")
        if hasattr(trainer, 'best_score'):
            st.metric("R² Score", f"{trainer.best_score:.4f}")
        
        if 'data' in st.session_state:
            current_data_size = len(st.session_state.data)
            st.metric("현재 데이터 수", f"{current_data_size}개")
    
    if st.button("다음 실험 조건 제안", type="primary"):
        try:
            suggestions = generate_bayesian_suggestions(
                trainer, promoters, n_suggestions, exploration_weight
            )
            
            st.subheader("제안된 실험 조건")
            
            # 제안 결과를 표로 표시
            suggestions_df = pd.DataFrame(suggestions)
            suggestions_df.index = [f"실험 {i+1}" for i in range(len(suggestions_df))]
            
            st.dataframe(suggestions_df, use_container_width=True)
            
            # CSV 다운로드 버튼
            csv = suggestions_df.to_csv(encoding='utf-8-sig')
            st.download_button(
                label="실험 조건 CSV 다운로드",
                data=csv,
                file_name=f"next_experiments_{st.session_state.current_project}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"베이지안 최적화 중 오류: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # 추가 데이터 학습 섹션  
    st.subheader("추가 데이터로 모델 업데이트")
    
    st.write("""
    새로운 실험 결과를 기존 데이터에 추가하여 모델을 재학습할 수 있습니다.
    이를 통해 점진적으로 모델 성능을 향상시킬 수 있습니다.
    """)
    
    additional_file = st.file_uploader(
        "추가 실험 데이터를 업로드하세요",
        type=['xlsx', 'csv'],
        help="기존 데이터와 동일한 형식의 파일",
        key="additional_data"
    )
    
    if additional_file is not None:
        try:
            # 추가 데이터 로드
            if additional_file.name.endswith('.xlsx'):
                additional_df = pd.read_excel(additional_file)
            else:
                additional_df = pd.read_csv(additional_file)
            
            st.write("**추가 데이터 미리보기:**")
            st.dataframe(additional_df.head(), use_container_width=True)
            
            if st.button("데이터 추가 및 모델 재학습", type="primary"):
                # 기존 데이터와 병합
                if 'data' in st.session_state:
                    combined_df = pd.concat([st.session_state.data, additional_df], ignore_index=True)
                    
                    # 중복 제거
                    before_dedup = len(combined_df)
                    combined_df = combined_df.drop_duplicates()
                    after_dedup = len(combined_df)
                    
                    if before_dedup > after_dedup:
                        st.info(f"중복된 {before_dedup - after_dedup}개 행을 제거했습니다.")
                    
                    # 세션 상태 업데이트
                    st.session_state.data = combined_df
                    
                    # 프로젝트에 저장
                    save_project_data(st.session_state.current_project, "raw_data", combined_df)
                    update_project_metadata(st.session_state.current_project, data_count=len(combined_df))
                    
                    # 세션 상태 저장
                    save_project_session_state(st.session_state.current_project)
                    
                    st.success(f"데이터가 업데이트되었습니다! 총 {len(combined_df)}개 데이터")
                    st.info("사이드바에서 'ML 모델 학습' 메뉴로 이동하여 모델을 재학습하세요.")
                    
                else:
                    st.error("기존 데이터가 없습니다. 먼저 초기 데이터를 업로드해주세요.")
                    
        except Exception as e:
            st.error(f"추가 데이터 처리 중 오류: {str(e)}")
    
    # 완료 메시지
    if st.session_state.current_project:
        has_model = 'trainer' in st.session_state and st.session_state.trainer is not None
        has_results = 'model_results' in st.session_state and st.session_state.model_results is not None
        
        if has_model and has_results:
            st.markdown("---")
            st.success("🎉 모든 주요 작업이 완료되었습니다!")
            st.info("이제 새로운 실험 데이터를 추가하여 모델을 재학습하거나, 새로운 프로젝트를 시작할 수 있습니다.")


def show_help():
    """도움말 페이지"""
    st.header("도움말")
    
    st.markdown("""
    ### 사용법 가이드
    
    #### 1. 프로젝트 관리
    - **새 프로젝트 생성**: 메인 메뉴에서 "새 프로젝트 생성" 선택, 실험별로 별도 프로젝트 권장
    - **프로젝트 선택**: 사이드바에서 기존 프로젝트 선택하여 작업 이어가기
    - **진행상황 추적**: 사이드바에서 Cycle 및 데이터 현황, 저장된 상태 정보 확인
    
    #### 2. 데이터 준비
    - **파일 형식**: Excel (.xlsx) 또는 CSV (.csv)
    - **필수 컬럼**:
      - `CrtYB`, `CrtI`, `CrtE`: Promoter 정보
      - `avg`: 베타카로틴 titer (예측 타겟)
    
    #### 3. 모델 설정 권장사항
    - **모델 전략**: "선형 모델 중심" (베타카로틴 데이터에 최적화)
    - **인코딩**: "자동 선택" (One-Hot 인코딩 우선)
    - **타겟 변환**: "자동 선택" (Log 변환으로 성능 향상)
    
    #### 4. 성능 해석
    - **R² > 0.7**: 우수한 성능
    - **R² 0.3-0.7**: 보통 성능
    - **R² < 0.3**: 성능 개선 필요
    - **R² < 0**: 베이스라인보다 낮음 (데이터 품질 검토 필요)
    
    ### 기술적 특징
    
    #### 프로젝트 데이터 관리
    - **자동 저장**: 데이터 업로드 및 모델 학습 시 자동 저장
    - **진행상황**: Cycle 수와 총 데이터 개수 추적
    - **지속성**: 프로젝트 간 데이터 독립적 관리
    
    #### 범주형 데이터 처리
    - **One-Hot 인코딩**: Promoter 간 독립적 효과 분석
    - **Label 인코딩**: 순서 관계 가정 (권장하지 않음)
    
    #### 타겟 변수 변환
    - **Log 변환**: 왜도 > 1.0이고 0값이 있을 때 자동 적용
    - **Square Root 변환**: 분산 안정화
    
    #### 모델 종류
    - **Linear Regression**: 기본 선형 모델
    - **Ridge**: L2 정규화 (과적합 방지)
    - **Lasso**: L1 정규화 (자동 특성 선택)
    - **ElasticNet**: L1 + L2 정규화 (균형 잡힌 접근)
    - **Polynomial**: 비선형 관계 포착
    
    ### 문제 해결
    
    #### 자주 발생하는 오류
    1. **"프로젝트를 선택해주세요"**: 프로젝트 관리에서 프로젝트 생성/선택
    2. **"특성 변수를 선택해주세요"**: CrtYB, CrtI, CrtE 컬럼을 선택
    3. **음수 R² 점수**: 데이터 품질 문제 → 더 많은 데이터 또는 전처리 필요
    4. **과적합 경고**: 정규화 모델(Ridge, Lasso) 사용 권장
    
    #### 성능 개선 방법
    1. **더 많은 데이터**: 최소 100개 이상의 실험 결과
    2. **특성 엔지니어링**: Promoter 간 상호작용 추가
    3. **이상값 제거**: 실험 오류 데이터 정제
    4. **타겟 변환**: Log 또는 Square Root 변환
    """)


if __name__ == "__main__":
    main()