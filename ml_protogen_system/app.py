import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
from sklearn.metrics import mean_squared_error, r2_score
from ml_core import MLModelTrainer, BayesianOptimizer, MappingFileGenerator
from project_manager import ProjectDataManager
from test_data_generator import generate_test_experiment_results


class ProjectManager:
    def __init__(self):
        self.fixed_steps = [
            "프로젝트 설정",
            "초기 데이터 입력", 
            "초기 모델 학습"
        ]
        self.cycle_steps = [
            "모델 예측 및 분석",
            "실험 설계", 
            "매핑 파일 생성",
            "결과 입력 및 모델 업데이트"
        ]
        self.current_step = 0
        self.current_cycle = 0
        self.project_data = {}
        self.in_cycle_phase = False
    
    def init_session_state(self):
        """세션 상태 초기화"""
        if 'project_manager' not in st.session_state:
            st.session_state.project_manager = self
        if 'data_manager' not in st.session_state:
            st.session_state.data_manager = ProjectDataManager()
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'project_list' not in st.session_state:
            st.session_state.project_list = st.session_state.data_manager.get_project_list()
        if 'current_step' not in st.session_state:
            st.session_state.current_step = 0
        if 'current_cycle' not in st.session_state:
            st.session_state.current_cycle = 0
        if 'in_cycle_phase' not in st.session_state:
            st.session_state.in_cycle_phase = False
        if 'project_data' not in st.session_state:
            st.session_state.project_data = {}
        if 'ml_trainer' not in st.session_state:
            st.session_state.ml_trainer = MLModelTrainer(model_preference='linear_focused', encoding_method='auto', target_transform='auto')
        if 'bayesian_optimizer' not in st.session_state:
            st.session_state.bayesian_optimizer = None
        if 'mapping_generator' not in st.session_state:
            st.session_state.mapping_generator = MappingFileGenerator()
        if 'cycle_data' not in st.session_state:
            st.session_state.cycle_data = []  # 각 사이클의 데이터를 저장
        if 'all_training_data' not in st.session_state:
            st.session_state.all_training_data = pd.DataFrame()  # 누적 학습 데이터
    
    def safe_dataframe_display(self, df, **kwargs):
        """Arrow 호환성을 보장하는 안전한 DataFrame 표시"""
        if df is None or df.empty:
            st.write("표시할 데이터가 없습니다.")
            return
        
        # DataFrame 복사본 생성
        safe_df = df.copy()
        
        # 각 컬럼의 데이터 타입을 안전하게 변환
        for col in safe_df.columns:
            if safe_df[col].dtype == 'object':
                # 혼합 타입 컬럼 처리
                try:
                    # 먼저 수치형 변환 시도
                    safe_df[col] = pd.to_numeric(safe_df[col], errors='ignore')
                    # 여전히 object 타입이면 문자열로 변환
                    if safe_df[col].dtype == 'object':
                        safe_df[col] = safe_df[col].astype(str)
                except Exception:
                    # 모든 것이 실패하면 문자열로 강제 변환
                    safe_df[col] = safe_df[col].astype(str)
            elif str(safe_df[col].dtype).startswith('float'):
                # float 타입은 명시적으로 float64로 변환
                safe_df[col] = safe_df[col].astype(float)
            elif str(safe_df[col].dtype).startswith('int'):
                # int 타입은 명시적으로 int64로 변환
                safe_df[col] = safe_df[col].astype(int)
        
        # 안전한 DataFrame 표시
        try:
            st.dataframe(safe_df, **kwargs)
        except Exception as e:
            # 최후의 수단: 모든 컬럼을 문자열로 변환
            str_df = safe_df.astype(str)
            st.dataframe(str_df, **kwargs)
            st.warning(f"DataFrame 표시 중 타입 변환 문제가 발생하여 문자열로 변환했습니다: {str(e)}")
    
    def save_cycle_data(self, cycle_num: int, results_data: pd.DataFrame):
        """사이클별 결과 데이터를 파일로 저장"""
        if st.session_state.current_project is None:
            return
        
        project_path = os.path.join("projects", st.session_state.current_project)
        cycles_path = os.path.join(project_path, "cycles")
        
        # 사이클 디렉토리 생성
        os.makedirs(cycles_path, exist_ok=True)
        
        # 결과 데이터 CSV로 저장
        cycle_data_path = os.path.join(cycles_path, f"cycle_{cycle_num}_results.csv")
        results_data.to_csv(cycle_data_path, index=False, encoding='utf-8-sig')
        
        # 메타데이터 저장
        metadata = {
            "cycle_number": cycle_num,
            "timestamp": datetime.now().isoformat(),
            "data_count": len(results_data),
            "columns": list(results_data.columns)
        }
        
        metadata_path = os.path.join(cycles_path, f"cycle_{cycle_num}_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        st.success(f"사이클 {cycle_num} 데이터가 저장되었습니다: {cycle_data_path}")
    
    def update_training_data(self, new_results: pd.DataFrame) -> pd.DataFrame:
        """누적 학습 데이터를 업데이트하고 파일로 저장"""
        if st.session_state.current_project is None:
            return pd.DataFrame()
        
        project_path = os.path.join("projects", st.session_state.current_project)
        data_path = os.path.join(project_path, "data")
        os.makedirs(data_path, exist_ok=True)
        
        # 기존 누적 데이터 로드
        training_data_path = os.path.join(data_path, "all_training_data.csv")
        
        if os.path.exists(training_data_path):
            # 파일에서 기존 데이터 로드
            existing_data = pd.read_csv(training_data_path)
        else:
            # 초기 데이터부터 시작
            if 'initial_data' in st.session_state.project_data:
                existing_data = pd.DataFrame(st.session_state.project_data['initial_data'])
            else:
                existing_data = pd.DataFrame()
        
        # 새 결과 데이터 추가
        if not existing_data.empty:
            updated_data = pd.concat([existing_data, new_results], ignore_index=True)
        else:
            updated_data = new_results.copy()
        
        # 중복 제거 (혹시 모를 중복 데이터 방지)
        updated_data = updated_data.drop_duplicates().reset_index(drop=True)
        
        # 파일로 저장
        updated_data.to_csv(training_data_path, index=False, encoding='utf-8-sig')
        
        # 세션 상태도 업데이트
        st.session_state.all_training_data = updated_data
        
        st.info(f"누적 학습 데이터 업데이트 완료: {len(updated_data)}개 샘플")
        return updated_data
    
    def save_model(self, trainer, cycle_num: int):
        """학습된 모델을 파일로 저장"""
        if st.session_state.current_project is None:
            return
        
        project_path = os.path.join("projects", st.session_state.current_project)
        models_path = os.path.join(project_path, "models")
        os.makedirs(models_path, exist_ok=True)
        
        # 현재 최고 성능 모델 저장
        current_model_path = os.path.join(models_path, "current_best_model.joblib")
        trainer.save_model(current_model_path)
        
        # 사이클별 모델도 별도 저장 (히스토리 관리)
        cycle_model_path = os.path.join(models_path, f"model_cycle_{cycle_num}.joblib")
        trainer.save_model(cycle_model_path)
        
        # 모델 성능 히스토리 저장
        model_history = {
            "cycle": cycle_num,
            "best_score": trainer.best_score,
            "best_model": trainer.best_model_name,
            "timestamp": datetime.now().isoformat(),
            "model_path": cycle_model_path
        }
        
        history_path = os.path.join(models_path, "model_history.json")
        
        # 기존 히스토리 로드
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                history_list = json.load(f)
        else:
            history_list = []
        
        # 새 히스토리 추가
        history_list.append(model_history)
        
        # 히스토리 저장
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, indent=2, ensure_ascii=False)
        
        st.success(f"모델이 저장되었습니다: {current_model_path}")
    
    def load_training_data(self) -> pd.DataFrame:
        """저장된 누적 학습 데이터 로드"""
        if st.session_state.current_project is None:
            return pd.DataFrame()
        
        project_path = os.path.join("projects", st.session_state.current_project)
        training_data_path = os.path.join(project_path, "data", "all_training_data.csv")
        
        if os.path.exists(training_data_path):
            try:
                data = pd.read_csv(training_data_path)
                st.session_state.all_training_data = data
                return data
            except Exception as e:
                st.error(f"학습 데이터 로드 중 오류: {str(e)}")
                return pd.DataFrame()
        else:
            # 파일이 없으면 초기 데이터 사용
            if 'initial_data' in st.session_state.project_data:
                initial_data = pd.DataFrame(st.session_state.project_data['initial_data'])
                return initial_data
            return pd.DataFrame()
    
    def save_initial_training_data(self, df: pd.DataFrame):
        """초기 학습 데이터를 파일로 저장"""
        if st.session_state.current_project is None:
            return
        
        project_path = os.path.join("projects", st.session_state.current_project)
        data_path = os.path.join(project_path, "data")
        os.makedirs(data_path, exist_ok=True)
        
        # 초기 데이터 저장
        initial_data_path = os.path.join(data_path, "initial_data.csv")
        df.to_csv(initial_data_path, index=False, encoding='utf-8-sig')
        
        # 누적 학습 데이터로도 저장 (첫 번째 데이터)
        training_data_path = os.path.join(data_path, "all_training_data.csv")
        df.to_csv(training_data_path, index=False, encoding='utf-8-sig')
        
        # 세션 상태 업데이트
        st.session_state.all_training_data = df.copy()
        
        st.success(f"초기 학습 데이터가 저장되었습니다: {len(df)}개 샘플")
    
    def show_project_structure(self):
        """프로젝트 폴더 구조 표시 (디버깅용)"""
        if st.session_state.current_project is None:
            st.warning("활성 프로젝트가 없습니다.")
            return
        
        with st.expander("📁 프로젝트 폴더 구조"):
            project_path = os.path.join("projects", st.session_state.current_project)
            
            if os.path.exists(project_path):
                st.write(f"**프로젝트 경로:** `{project_path}`")
                
                # 폴더 구조 재귀적으로 표시
                def show_directory_tree(path, prefix=""):
                    items = []
                    if os.path.exists(path):
                        for item in sorted(os.listdir(path)):
                            item_path = os.path.join(path, item)
                            if os.path.isdir(item_path):
                                items.append(f"{prefix}📁 {item}/")
                                # 하위 폴더 내용도 표시
                                sub_items = show_directory_tree(item_path, prefix + "  ")
                                items.extend(sub_items)
                            else:
                                # 파일 크기 정보 포함
                                try:
                                    size = os.path.getsize(item_path)
                                    if size > 1024*1024:  # MB
                                        size_str = f"{size/(1024*1024):.1f} MB"
                                    elif size > 1024:  # KB
                                        size_str = f"{size/1024:.1f} KB"
                                    else:
                                        size_str = f"{size} B"
                                    items.append(f"{prefix}📄 {item} ({size_str})")
                                except:
                                    items.append(f"{prefix}📄 {item}")
                    return items
                
                tree_items = show_directory_tree(project_path)
                for item in tree_items:
                    st.text(item)
            else:
                st.error(f"프로젝트 폴더가 존재하지 않습니다: {project_path}")
    
    def create_project_sidebar(self):
        """프로젝트 선택 사이드바 생성"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.title("🧬 ML Protogen System")
        
        with col2:
            if st.button("새로고침", help="프로젝트 목록 새로고침"):
                st.session_state.project_list = st.session_state.data_manager.get_project_list()
                st.rerun()
        
        st.markdown("---")
        
        # 프로젝트 목록
        st.markdown("### 📁 프로젝트 목록")
        
        if not st.session_state.project_list:
            st.info("생성된 프로젝트가 없습니다. 새 프로젝트를 만들어보세요!")
        else:
            # 현재 선택된 프로젝트 표시
            if st.session_state.current_project:
                current_info = st.session_state.data_manager.get_project_info(st.session_state.current_project)
                if current_info:
                    st.success(f"**현재 프로젝트:** {current_info.get('project_name', 'Unknown')}")
            
            # 프로젝트 선택
            for project_safe_name in st.session_state.project_list:
                project_info = st.session_state.data_manager.get_project_info(project_safe_name)
                if not project_info:
                    continue
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    if st.button(
                        f"📊 {project_info.get('project_name', project_safe_name)}", 
                        key=f"select_{project_safe_name}",
                        help=f"생성일: {project_info.get('created_at', 'Unknown')[:10]}"
                    ):
                        self.load_project(project_safe_name)
                
                with col2:
                    if st.button("💾", key=f"save_{project_safe_name}", help="저장"):
                        if st.session_state.current_project == project_safe_name:
                            self.save_current_project()
                            st.success("저장됨!")
                        else:
                            st.warning("먼저 프로젝트를 선택하세요.")
                
                with col3:
                    if st.button("🗑️", key=f"delete_{project_safe_name}", help="삭제"):
                        if st.button(f"정말 삭제하시겠습니까? {project_info.get('project_name')}", 
                                   key=f"confirm_delete_{project_safe_name}"):
                            try:
                                st.session_state.data_manager.delete_project(project_safe_name)
                                st.session_state.project_list = st.session_state.data_manager.get_project_list()
                                if st.session_state.current_project == project_safe_name:
                                    st.session_state.current_project = None
                                    self.reset_session_for_new_project()
                                st.success("프로젝트가 삭제되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 실패: {str(e)}")
                
                # 프로젝트 정보 표시
                if project_info:
                    with st.expander(f"ℹ️ {project_info.get('project_name', project_safe_name)} 정보"):
                        st.write(f"**생성일:** {project_info.get('created_at', 'Unknown')[:19]}")
                        st.write(f"**단계:** {project_info.get('current_step', 0) + 1}")
                        st.write(f"**사이클:** {project_info.get('current_cycle', 0)}")
                        st.write(f"**데이터 수:** {project_info.get('data_count', 0)}")
        
        # 새 프로젝트 생성
        st.markdown("---")
        st.markdown("### ➕ 새 프로젝트 생성")
        
        with st.expander("새 프로젝트 만들기"):
            new_project_name = st.text_input("프로젝트 이름", key="new_project_name")
            new_project_description = st.text_area("프로젝트 설명", key="new_project_desc")
            
            if st.button("프로젝트 생성", key="create_project"):
                if new_project_name.strip():
                    try:
                        safe_name = st.session_state.data_manager.create_project(new_project_name.strip())
                        st.session_state.project_list = st.session_state.data_manager.get_project_list()
                        
                        # 새 프로젝트로 전환
                        self.load_project(safe_name)
                        
                        # 초기 프로젝트 설명 저장
                        if new_project_description.strip():
                            st.session_state.project_data['project_description'] = new_project_description.strip()
                        
                        st.success(f"프로젝트 '{new_project_name}'이 생성되었습니다!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"프로젝트 생성 실패: {str(e)}")
                else:
                    st.warning("프로젝트 이름을 입력해주세요.")
    
    def create_unified_sidebar(self):
        """통합 사이드바 생성"""
        with st.sidebar:
            st.title("🧬 ML Protogen System")
            
            # 프로젝트 선택
            st.markdown("### 📁 프로젝트 선택")
            
            # 프로젝트 목록 가져오기
            project_options = ["새 프로젝트 생성..."] + st.session_state.project_list
            
            # 현재 선택된 프로젝트의 인덱스 찾기
            current_index = 0
            if st.session_state.current_project and st.session_state.current_project in st.session_state.project_list:
                current_index = st.session_state.project_list.index(st.session_state.current_project) + 1
            
            # 프로젝트 선택 박스
            selected_option = st.selectbox(
                "프로젝트를 선택하세요:",
                project_options,
                index=current_index,
                key="project_selector"
            )
            
            # 선택된 프로젝트 처리
            if selected_option == "새 프로젝트 생성...":
                if st.session_state.current_project is not None:
                    # 새 프로젝트 생성 모드로 전환
                    st.session_state.current_project = None
                    self.reset_session_for_new_project()
                    st.rerun()
            elif selected_option != st.session_state.current_project:
                # 다른 프로젝트 선택
                if selected_option in st.session_state.project_list:
                    self.load_project(selected_option)
            
            # 새 프로젝트 생성 폼
            if not st.session_state.current_project:
                st.markdown("---")
                st.markdown("### ➕ 새 프로젝트 생성")
                
                new_project_name = st.text_input("프로젝트 이름", key="sidebar_new_project_name")
                new_project_description = st.text_area("프로젝트 설명", key="sidebar_new_project_desc")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("생성", key="sidebar_create_project"):
                        if new_project_name.strip():
                            try:
                                safe_name = st.session_state.data_manager.create_project(new_project_name.strip())
                                st.session_state.project_list = st.session_state.data_manager.get_project_list()
                                
                                # 새 프로젝트로 전환
                                self.load_project(safe_name)
                                
                                # 초기 프로젝트 설명 저장
                                if new_project_description.strip():
                                    st.session_state.project_data['project_description'] = new_project_description.strip()
                                
                                st.success(f"프로젝트 '{new_project_name}'이 생성되었습니다!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"프로젝트 생성 실패: {str(e)}")
                        else:
                            st.warning("프로젝트 이름을 입력해주세요.")
                
                with col2:
                    if st.button("샘플", key="sidebar_sample_project", help="샘플 프로젝트 생성"):
                        try:
                            from datetime import datetime
                            sample_name = f"Sample_Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            safe_name = st.session_state.data_manager.create_project(sample_name)
                            st.session_state.project_list = st.session_state.data_manager.get_project_list()
                            
                            # 샘플 프로젝트로 전환
                            self.load_project(safe_name)
                            
                            # 샘플 데이터 추가
                            st.session_state.project_data.update({
                                'project_name': sample_name,
                                'project_description': '샘플 프로젝트 - 프로테인 발현 최적화 데모',
                                'experiment_type': 'Protein Expression',
                                'optimization_target': 'Maximize',
                                'target_metric': 'Expression_Level',
                                'expected_samples': 50
                            })
                            
                            st.success("샘플 프로젝트가 생성되었습니다!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"샘플 프로젝트 생성 실패: {str(e)}")
            
            # 현재 프로젝트가 있는 경우 진행 단계 표시
            if st.session_state.current_project:
                self.create_progress_display()
    
    def create_progress_display(self):
        """진행 단계 표시"""
        st.markdown("---")
        st.markdown("### 📋 진행 단계")
        
        # 고정 단계 표시
        st.markdown("#### 초기 설정")
        for i, step in enumerate(self.fixed_steps):
            if i == st.session_state.current_step and not st.session_state.in_cycle_phase:
                st.markdown(f"**▶ {i+1}. {step}**")
            elif i < st.session_state.current_step or st.session_state.in_cycle_phase:
                st.markdown(f"✅ {i+1}. {step}")
            else:
                st.markdown(f"⏳ {i+1}. {step}")
        
        # 사이클 단계 표시
        if st.session_state.in_cycle_phase or st.session_state.current_cycle > 0:
            st.markdown("#### 실험 사이클")
            
            # 완료된 사이클들
            for cycle in range(st.session_state.current_cycle):
                st.markdown(f"✅ **사이클 {cycle + 1}** (완료)")
            
            # 현재 사이클
            if st.session_state.in_cycle_phase:
                st.markdown(f"**🔄 사이클 {st.session_state.current_cycle + 1}** (진행중)")
                
                cycle_step_offset = len(self.fixed_steps)
                for i, step in enumerate(self.cycle_steps):
                    step_index = cycle_step_offset + i
                    if step_index == st.session_state.current_step:
                        st.markdown(f"  **▶ {i+1}. {step}**")
                    elif step_index < st.session_state.current_step:
                        st.markdown(f"  ✅ {i+1}. {step}")
                    else:
                        st.markdown(f"  ⏳ {i+1}. {step}")
        
        # 프로젝트 정보
        st.markdown("---")
        st.markdown("### ℹ️ 프로젝트 정보")
        
        project_info = st.session_state.data_manager.get_project_info(st.session_state.current_project)
        if project_info:
            st.write(f"**이름:** {project_info.get('project_name', 'Unknown')}")
            if st.session_state.project_data.get('project_description'):
                st.write(f"**설명:** {st.session_state.project_data['project_description']}")
            st.write(f"**생성일:** {project_info.get('created_at', 'Unknown')[:10]}")
            
            if st.session_state.in_cycle_phase or st.session_state.current_cycle > 0:
                st.write(f"**완료된 사이클:** {st.session_state.current_cycle}")
                st.write(f"**총 학습 데이터:** {len(st.session_state.all_training_data)}")
        
        # 단계 이동 버튼
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀ 이전", key="prev_step_btn"):
                self.go_previous_step()
        
        with col2:
            if st.button("다음 ▶", key="next_step_btn"):
                self.go_next_step()
        
        # 사이클 관리 버튼
        if not st.session_state.in_cycle_phase and st.session_state.current_step >= len(self.fixed_steps):
            if st.button("🔄 새 실험 사이클", type="primary", key="start_cycle_btn"):
                self.start_new_cycle()
        
        if st.session_state.in_cycle_phase:
            if st.button("✅ 사이클 완료 & 새 사이클", key="complete_cycle_btn"):
                self.complete_cycle_and_start_new()
            
            if st.button("🏁 프로젝트 종료", key="end_project_btn"):
                self.end_project()
        
        # 프로젝트 관리 버튼
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 저장", key="sidebar_save_btn"):
                self.save_current_project()
                st.success("저장됨!")
        
        with col2:
            if st.button("🗑️ 삭제", key="sidebar_delete_btn"):
                if st.button("정말 삭제?", key="confirm_sidebar_delete"):
                    try:
                        project_name = st.session_state.project_data.get('project_name', 'Unknown')
                        st.session_state.data_manager.delete_project(st.session_state.current_project)
                        st.session_state.project_list = st.session_state.data_manager.get_project_list()
                        st.session_state.current_project = None
                        self.reset_session_for_new_project()
                        st.success(f"프로젝트 '{project_name}'이 삭제되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {str(e)}")
        
        # 디버깅 및 정보
        if st.session_state.current_project:
            st.markdown("---")
            if st.button("📁 프로젝트 구조", key="show_structure_btn"):
                st.session_state.show_project_structure = True
    
    def create_sidebar(self):
        """단계 진행 사이드바 생성"""
        with st.sidebar:
            st.title("프로젝트 진행 단계")
            
            # 고정 단계 표시
            st.markdown("### 초기 설정 단계")
            for i, step in enumerate(self.fixed_steps):
                if i == st.session_state.current_step and not st.session_state.in_cycle_phase:
                    st.markdown(f"**▶ {i+1}. {step}**")
                elif i < st.session_state.current_step or st.session_state.in_cycle_phase:
                    st.markdown(f"✅ {i+1}. {step}")
                else:
                    st.markdown(f"⏳ {i+1}. {step}")
            
            # 사이클 단계 표시
            if st.session_state.in_cycle_phase or st.session_state.current_cycle > 0:
                st.markdown("### 반복 실험 사이클")
                
                # 완료된 사이클들
                for cycle in range(st.session_state.current_cycle):
                    st.markdown(f"✅ **사이클 {cycle + 1}** (완료)")
                
                # 현재 사이클
                if st.session_state.in_cycle_phase:
                    st.markdown(f"**🔄 사이클 {st.session_state.current_cycle + 1}** (진행중)")
                    
                    cycle_step_offset = len(self.fixed_steps)
                    for i, step in enumerate(self.cycle_steps):
                        step_index = cycle_step_offset + i
                        if step_index == st.session_state.current_step:
                            st.markdown(f"  **▶ {i+1}. {step}**")
                        elif step_index < st.session_state.current_step:
                            st.markdown(f"  ✅ {i+1}. {step}")
                        else:
                            st.markdown(f"  ⏳ {i+1}. {step}")
            
            st.markdown("---")
            
            # 프로젝트 정보
            if 'project_name' in st.session_state.project_data:
                st.markdown("### 프로젝트 정보")
                st.write(f"**이름:** {st.session_state.project_data['project_name']}")
                st.write(f"**설명:** {st.session_state.project_data.get('project_description', 'N/A')}")
                
                if st.session_state.in_cycle_phase or st.session_state.current_cycle > 0:
                    st.write(f"**완료된 사이클:** {st.session_state.current_cycle}")
                    st.write(f"**총 학습 데이터:** {len(st.session_state.all_training_data)}")
            
            # 단계 이동 및 사이클 관리 버튼
            st.markdown("---")
            
            # 이전/다음 버튼
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("이전 단계"):
                    self.go_previous_step()
            
            with col2:
                if st.button("다음 단계"):
                    self.go_next_step()
            
            # 사이클 관리 버튼
            if not st.session_state.in_cycle_phase and st.session_state.current_step >= len(self.fixed_steps):
                if st.button("새 실험 사이클 시작", type="primary"):
                    self.start_new_cycle()
            
            if st.session_state.in_cycle_phase:
                if st.button("사이클 완료 및 새 사이클 시작"):
                    self.complete_cycle_and_start_new()
                
                if st.button("프로젝트 종료"):
                    self.end_project()
    
    def go_previous_step(self):
        """이전 단계로 이동"""
        if st.session_state.in_cycle_phase:
            if st.session_state.current_step > len(self.fixed_steps):
                st.session_state.current_step -= 1
        else:
            if st.session_state.current_step > 0:
                st.session_state.current_step -= 1
        st.rerun()
    
    def go_next_step(self):
        """다음 단계로 이동"""
        if st.session_state.in_cycle_phase:
            max_cycle_step = len(self.fixed_steps) + len(self.cycle_steps) - 1
            if st.session_state.current_step < max_cycle_step:
                st.session_state.current_step += 1
        else:
            if st.session_state.current_step < len(self.fixed_steps) - 1:
                st.session_state.current_step += 1
            elif st.session_state.current_step == len(self.fixed_steps) - 1:
                # 초기 모델 학습 완료 후 사이클 시작
                self.start_new_cycle()
        
        # 자동 저장
        self.auto_save()
        st.rerun()
    
    def start_new_cycle(self):
        """새로운 실험 사이클 시작"""
        st.session_state.in_cycle_phase = True
        st.session_state.current_step = len(self.fixed_steps)  # 모델 분석부터 시작
        
        # 자동 저장
        self.auto_save()
        st.rerun()
    
    def complete_cycle_and_start_new(self):
        """현재 사이클 완료하고 새 사이클 시작"""
        st.session_state.current_cycle += 1
        st.session_state.current_step = len(self.fixed_steps)  # 모델 분석부터 시작
        
        # 현재 사이클 데이터 저장
        if f'cycle_{st.session_state.current_cycle - 1}_results' in st.session_state.project_data:
            cycle_results = st.session_state.project_data[f'cycle_{st.session_state.current_cycle - 1}_results']
            st.session_state.cycle_data.append(cycle_results)
        
        st.rerun()
    
    def end_project(self):
        """프로젝트 종료"""
        st.session_state.in_cycle_phase = False
        st.session_state.current_step = len(self.fixed_steps) + len(self.cycle_steps)
        st.rerun()
    
    def step_project_setup(self):
        """1단계: 프로젝트 설정"""
        st.header("1. 프로젝트 설정")
        
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "프로젝트 이름", 
                value=st.session_state.project_data.get('project_name', ''),
                key="project_name_input"
            )
            
            project_description = st.text_area(
                "프로젝트 설명",
                value=st.session_state.project_data.get('project_description', ''),
                key="project_description_input"
            )
            
            experiment_type = st.selectbox(
                "실험 유형",
                ["Protein Expression", "Metabolic Engineering", "Gene Regulation", "Custom"],
                index=0 if 'experiment_type' not in st.session_state.project_data else 
                      ["Protein Expression", "Metabolic Engineering", "Gene Regulation", "Custom"].index(st.session_state.project_data['experiment_type'])
            )
        
        with col2:
            st.markdown("### 프로젝트 목표")
            optimization_target = st.selectbox(
                "최적화 목표",
                ["Maximize", "Minimize"],
                index=0 if 'optimization_target' not in st.session_state.project_data else 
                      ["Maximize", "Minimize"].index(st.session_state.project_data['optimization_target'])
            )
            
            target_metric = st.text_input(
                "목표 지표 (예: Protein_Expression_Level)",
                value=st.session_state.project_data.get('target_metric', ''),
                key="target_metric_input"
            )
            
            expected_samples = st.number_input(
                "예상 총 실험 샘플 수",
                min_value=10,
                max_value=1000,
                value=st.session_state.project_data.get('expected_samples', 50),
                step=10
            )
        
        if st.button("프로젝트 설정 저장"):
            st.session_state.project_data.update({
                'project_name': project_name,
                'project_description': project_description,
                'experiment_type': experiment_type,
                'optimization_target': optimization_target,
                'target_metric': target_metric,
                'expected_samples': expected_samples,
                'created_at': st.session_state.project_data.get('created_at', datetime.now().isoformat())
            })
            
            # 자동 저장
            self.auto_save()
            
            st.success("프로젝트 설정이 저장되었습니다!")
            
            # 자동으로 다음 단계로 이동
            if st.session_state.current_step == 0:
                st.session_state.current_step = 1
                self.auto_save()  # 단계 이동 후에도 자동 저장
                st.rerun()
    
    def step_initial_data_input(self):
        """2단계: 초기 데이터 입력"""
        st.header("2. 초기 실험 데이터 입력")
        
        # 데이터 입력 방식 선택
        data_input_method = st.radio(
            "데이터 입력 방식을 선택하세요:",
            ["파일 업로드", "수동 입력", "템플릿 다운로드"]
        )
        
        if data_input_method == "파일 업로드":
            uploaded_file = st.file_uploader(
                "CSV 또는 Excel 파일을 업로드하세요",
                type=['csv', 'xlsx', 'xls']
            )
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.write("업로드된 데이터 미리보기:")
                    self.safe_dataframe_display(df)
                    
                    # 컬럼 선택 섹션
                    st.write("### 📊 컬럼 선택")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 타겟 변수 선택
                        target_column = st.selectbox(
                            "🎯 타겟 변수(목표 지표)를 선택하세요:",
                            df.columns.tolist(),
                            help="예측하고자 하는 목표 변수 (예: 단백질 발현량, 수율 등)"
                        )
                    
                    with col2:
                        # 데이터 타입별 컬럼 정보 표시
                        st.write("**컬럼 정보:**")
                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                        
                        if numeric_cols:
                            st.write(f"📊 수치형 ({len(numeric_cols)}개): {', '.join(numeric_cols[:3])}{'...' if len(numeric_cols) > 3 else ''}")
                        if categorical_cols:
                            st.write(f"📝 범주형 ({len(categorical_cols)}개): {', '.join(categorical_cols[:3])}{'...' if len(categorical_cols) > 3 else ''}")
                    
                    # 특성 컬럼 선택
                    st.write("### 🔧 특성 컬럼 선택")
                    
                    # 자동 제외 후보 컬럼들 표시
                    exclude_patterns = ['Sample_ID', 'sample_id', 'ID', 'id', 'Unnamed:', 'unnamed:', 'Well', 'well', 'Index', 'index']
                    auto_exclude_candidates = []
                    for col in df.columns:
                        if col == target_column:
                            continue
                        for pattern in exclude_patterns:
                            if pattern in col:
                                auto_exclude_candidates.append(col)
                                break
                    
                    # 특성 컬럼 후보들 (타겟 제외)
                    available_features = [col for col in df.columns if col != target_column]
                    
                    # 자동 제외 제안
                    if auto_exclude_candidates:
                        st.write("**🤖 자동 제외 제안:**")
                        st.info(f"식별자로 보이는 컬럼들: {', '.join(auto_exclude_candidates)}")
                        
                        # 기본 선택: 자동 제외 후보들을 제외한 나머지
                        default_features = [col for col in available_features if col not in auto_exclude_candidates]
                    else:
                        default_features = available_features
                    
                    # 특성 컬럼 다중 선택
                    selected_features = st.multiselect(
                        "🎛️ ML 학습에 사용할 특성 컬럼들을 선택하세요:",
                        options=available_features,
                        default=default_features,
                        help="실험 조건이나 설정값 등 예측에 사용할 변수들을 선택하세요"
                    )
                    
                    # 선택된 컬럼 요약
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("타겟 변수", "1개", delta=target_column)
                    with col2:
                        st.metric("특성 변수", f"{len(selected_features)}개")
                    with col3:
                        excluded_count = len(df.columns) - len(selected_features) - 1  # -1 for target
                        st.metric("제외된 변수", f"{excluded_count}개")
                    
                    # 선택된 컬럼들 표시
                    if selected_features:
                        st.write("**✅ 선택된 특성 컬럼들:**")
                        feature_info = []
                        for col in selected_features:
                            col_type = "수치형" if col in numeric_cols else "범주형"
                            unique_count = df[col].nunique()
                            feature_info.append(f"• **{col}** ({col_type}, 고유값: {unique_count}개)")
                        
                        for info in feature_info[:10]:  # 최대 10개만 표시
                            st.write(info)
                        if len(feature_info) > 10:
                            st.write(f"... 외 {len(feature_info) - 10}개")
                    
                    # 경고 및 검증
                    if not selected_features:
                        st.error("⚠️ 최소 1개 이상의 특성 컬럼을 선택해야 합니다!")
                    elif len(selected_features) > 50:
                        st.warning(f"⚠️ 선택된 특성이 너무 많습니다 ({len(selected_features)}개). 성능을 위해 중요한 특성들만 선택하는 것을 권장합니다.")
                    
                    if st.button("✅ 데이터 확인 및 저장", disabled=not selected_features):
                        if not selected_features:
                            st.error("특성 컬럼을 선택해주세요!")
                            return
                        
                        # 사용자가 선택한 컬럼들 저장
                        st.session_state.project_data['initial_data'] = df.to_dict('records')
                        st.session_state.project_data['target_column'] = target_column
                        st.session_state.project_data['feature_columns'] = selected_features
                        
                        # 제외된 컬럼들 정보
                        excluded_columns = [col for col in df.columns if col != target_column and col not in selected_features]
                        
                        # 로깅 정보
                        print(f"🔍 전체 컬럼 ({len(df.columns)}개): {list(df.columns)}")
                        print(f"🎯 타겟 컬럼: {target_column}")
                        print(f"✅ 선택된 특성 컬럼 ({len(selected_features)}개): {selected_features}")
                        print(f"❌ 제외된 컬럼 ({len(excluded_columns)}개): {excluded_columns}")
                        
                        # 선택 결과 표시
                        st.success("데이터가 성공적으로 저장되었습니다!")
                        
                        with st.expander("📋 저장된 설정 확인", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**🎯 타겟 변수:**")
                                st.code(target_column)
                                
                                st.write(f"**✅ 선택된 특성 ({len(selected_features)}개):**")
                                for feature in selected_features:
                                    st.write(f"• {feature}")
                            
                            with col2:
                                if excluded_columns:
                                    st.write(f"**❌ 제외된 컬럼 ({len(excluded_columns)}개):**")
                                    for col in excluded_columns:
                                        st.write(f"• {col}")
                                else:
                                    st.write("**모든 컬럼이 사용됩니다!**")
                        
                        # 자동 저장
                        self.auto_save()
                        st.success("초기 데이터가 저장되었습니다!")
                        
                except Exception as e:
                    st.error(f"파일 읽기 오류: {str(e)}")
        
        elif data_input_method == "수동 입력":
            st.markdown("### 실험 조건 수동 입력")
            
            # 변수 정의
            if 'manual_variables' not in st.session_state:
                st.session_state.manual_variables = [
                    {'name': 'Promoter', 'type': 'categorical', 'values': ['P1', 'P2', 'P3']},
                    {'name': 'Temperature', 'type': 'numerical', 'min': 25, 'max': 37},
                ]
            
            # 변수 관리
            st.markdown("#### 실험 변수 정의")
            for i, var in enumerate(st.session_state.manual_variables):
                col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
                
                with col1:
                    var['name'] = st.text_input(f"변수 이름 {i+1}", value=var['name'], key=f"var_name_{i}")
                
                with col2:
                    var['type'] = st.selectbox(f"타입 {i+1}", ['categorical', 'numerical'], 
                                             index=0 if var['type'] == 'categorical' else 1, key=f"var_type_{i}")
                
                with col3:
                    if var['type'] == 'categorical':
                        values_str = ', '.join(var.get('values', []))
                        new_values = st.text_input(f"값들 {i+1} (쉼표 구분)", value=values_str, key=f"var_values_{i}")
                        var['values'] = [v.strip() for v in new_values.split(',') if v.strip()]
                    else:
                        col31, col32 = st.columns(2)
                        with col31:
                            var['min'] = st.number_input(f"최소값 {i+1}", value=var.get('min', 0), key=f"var_min_{i}")
                        with col32:
                            var['max'] = st.number_input(f"최대값 {i+1}", value=var.get('max', 100), key=f"var_max_{i}")
                
                with col4:
                    if st.button(f"삭제 {i+1}", key=f"del_var_{i}"):
                        st.session_state.manual_variables.pop(i)
                        st.rerun()
            
            if st.button("변수 추가"):
                st.session_state.manual_variables.append({
                    'name': f'Variable_{len(st.session_state.manual_variables)+1}',
                    'type': 'categorical',
                    'values': ['Value1', 'Value2']
                })
                st.rerun()
        
        elif data_input_method == "템플릿 다운로드":
            st.markdown("### 데이터 입력 템플릿")
            
            # 샘플 템플릿 생성
            template_data = {
                'Promoter': ['P1', 'P2', 'P3', 'P1', 'P2'],
                'CDS': ['Gene_A', 'Gene_B', 'Gene_A', 'Gene_C', 'Gene_B'],
                'Temperature': [30, 32, 28, 35, 30],
                'pH': [7.0, 7.5, 6.8, 7.2, 7.0],
                'Expression_Level': [120, 85, 95, 140, 110]
            }
            
            template_df = pd.DataFrame(template_data)
            st.write("템플릿 예시:")
            self.safe_dataframe_display(template_df)
            
            csv_template = template_df.to_csv(index=False)
            st.download_button(
                label="CSV 템플릿 다운로드",
                data=csv_template,
                file_name="experiment_template.csv",
                mime="text/csv"
            )
        
        # 저장된 데이터 표시
        if 'initial_data' in st.session_state.project_data:
            st.markdown("### 저장된 초기 데이터")
            df_saved = pd.DataFrame(st.session_state.project_data['initial_data'])
            self.safe_dataframe_display(df_saved)
            
            st.write(f"**타겟 변수:** {st.session_state.project_data.get('target_column', 'N/A')}")
            st.write(f"**특성 변수:** {', '.join(st.session_state.project_data.get('feature_columns', []))}")
    
    def step_initial_ml_training(self):
        """3단계: 초기 ML 모델 학습"""
        st.header("3. 초기 ML 모델 학습")
        
        if 'initial_data' not in st.session_state.project_data:
            st.warning("먼저 초기 데이터를 입력해주세요.")
            return
        
        df = pd.DataFrame(st.session_state.project_data['initial_data'])
        target_column = st.session_state.project_data['target_column']
        
        st.write("### 학습 데이터 요약")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**데이터 형태:**")
            st.write(f"- 샘플 수: {len(df)}")
            st.write(f"- 특성 수: {len(df.columns) - 1}")
            st.write(f"- 타겟 변수: {target_column}")
        
        with col2:
            st.write("**타겟 변수 통계:**")
            st.write(df[target_column].describe())
        
        # 데이터 분포 시각화
        fig = px.histogram(df, x=target_column, title=f"{target_column} 분포")
        st.plotly_chart(fig, use_container_width=True)
        
        # ML 모델 학습 섹션
        st.write("### 🤖 ML 모델 학습")
        
        # 모델 및 인코딩 선택 옵션
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📋 모델 선택 전략:**")
            model_strategy = st.selectbox(
                "데이터 특성에 맞는 모델 전략을 선택하세요",
                options=['linear_focused', 'ensemble_focused', 'all'],
                format_func=lambda x: {
                    'linear_focused': '🔸 선형 모델 중심 (소규모/노이즈 많은 데이터 권장)',
                    'ensemble_focused': '🔹 앙상블 모델 중심 (대규모 데이터 권장)', 
                    'all': '🔷 모든 모델 (전체 비교)'
                }[x],
                index=0,  # 기본값: linear_focused
                help="""
                • **선형 모델 중심**: LinearRegression, Ridge, Lasso, ElasticNet, Polynomial 포함. 소규모 데이터나 노이즈가 많은 데이터에 적합
                • **앙상블 모델 중심**: RandomForest, GradientBoosting 포함. 대규모이고 복잡한 패턴이 있는 데이터에 적합
                • **모든 모델**: 모든 모델을 비교하여 최적 모델 선택
                """
            )
        
        with col2:
            st.write("**🏷️ 범주형 데이터 인코딩:**")
            encoding_method = st.selectbox(
                "범주형 데이터 처리 방법을 선택하세요",
                options=['auto', 'label', 'onehot_drop', 'onehot'],
                format_func=lambda x: {
                    'auto': '🤖 자동 선택 (One-Hot 우선)',
                    'label': '🏷️ Label Encoding (순서 관계 가정)',
                    'onehot_drop': '🔥 One-Hot (다중공선성 방지)',
                    'onehot': '🔥 One-Hot (전체 생성)'
                }[x],
                index=0,  # 기본값: auto
                help="""
                • **자동 선택**: 기본적으로 One-Hot 선호 (생물학적 데이터에 적합)
                • **Label Encoding**: 범주를 0,1,2... 숫자로 변환 (순서 관계 암시)
                • **One-Hot (다중공선성 방지)**: 각 범주를 0/1 컬럼으로 변환, 첫 번째 범주 제거
                • **One-Hot (전체)**: 모든 범주를 0/1 컬럼으로 변환
                
                **추천**: Promoter 같은 명목형 데이터는 One-Hot이 생물학적으로 더 적합
                """
            )
        
        # 타겟 변수 변환 옵션 추가
        st.write("**📈 타겟 변수 변환:**")
        target_transform = st.selectbox(
            "타겟 변수(avg) 변환 방법을 선택하세요",
            options=['auto', 'none', 'log', 'sqrt'],
            format_func=lambda x: {
                'auto': '🤖 자동 선택 (분포에 따라)',
                'none': '📊 변환 없음',
                'log': '📈 Log 변환 (왜도 개선)',
                'sqrt': '📐 Square Root 변환 (분산 안정화)'
            }[x],
            index=0,  # 기본값: auto
            help="""
            • **자동 선택**: 데이터의 왜도와 분포를 분석하여 최적 변환 방법 선택
            • **변환 없음**: 원본 데이터 그대로 사용
            • **Log 변환**: log(y + 1) 적용. 왜도가 높고 0값이 있을 때 유용
            • **Square Root 변환**: √y 적용. 분산을 안정화하고 왜도 개선
            
            **베타카로틴 데이터**: 0값이 있고 왜도가 높아서 Log 변환이 도움될 수 있음
            """
        )
        
        # 모델 전략, 인코딩 방법, 타겟 변환 변경 시 새로운 trainer 생성
        current_config = (model_strategy, encoding_method, target_transform)
        if ('current_config' not in st.session_state or 
            st.session_state.current_config != current_config):
            
            st.session_state.current_config = current_config
            st.session_state.ml_trainer = MLModelTrainer(
                model_preference=model_strategy, 
                encoding_method=encoding_method,
                target_transform=target_transform
            )
            st.session_state.ml_training_step = 0  # 단계 초기화
            st.info(f"설정이 변경되었습니다 (모델: {model_strategy}, 인코딩: {encoding_method}, 타겟변환: {target_transform}). 다시 학습을 진행해주세요.")
        
        # 사전 검증
        feature_columns = st.session_state.project_data.get('feature_columns', [])
        if not feature_columns:
            st.error("먼저 특성 컬럼을 선택해주세요!")
            return
        
        # 학습 전 데이터 분석
        with st.expander("📊 학습 전 데이터 분석", expanded=False):
            st.write("**선택된 특성 컬럼 분석:**")
            
            col1, col2 = st.columns(2)
            with col1:
                for feature in feature_columns:
                    if feature in df.columns:
                        unique_count = df[feature].nunique()
                        data_type = "범주형" if df[feature].dtype == 'object' else "수치형"
                        st.write(f"• **{feature}**: {data_type}, {unique_count}개 고유값")
            
            with col2:
                st.write(f"**타겟 변수 ({target_column}) 분석:**")
                st.write(f"• 범위: {df[target_column].min():.3f} ~ {df[target_column].max():.3f}")
                st.write(f"• 평균: {df[target_column].mean():.3f}")
                st.write(f"• 표준편차: {df[target_column].std():.3f}")
                st.write(f"• 고유값: {df[target_column].nunique()}개")
        
        # 학습 진행 단계
        if 'ml_training_step' not in st.session_state:
            st.session_state.ml_training_step = 0
        
        # 단계별 버튼들
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("1️⃣ 데이터 전처리", disabled=st.session_state.ml_training_step > 0):
                with st.spinner("데이터를 전처리하고 있습니다..."):
                    try:
                        trainer = st.session_state.ml_trainer
                        
                        # 데이터 전처리
                        X, y = trainer.preprocess_data(df, target_column, feature_columns)
                        
                        # 세션에 저장
                        st.session_state.preprocessed_X = X
                        st.session_state.preprocessed_y = y
                        st.session_state.ml_training_step = 1
                        
                        st.success("✅ 데이터 전처리 완료!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"전처리 중 오류: {str(e)}")
        
        with col2:
            if st.button("2️⃣ 모델 학습", disabled=st.session_state.ml_training_step != 1):
                with st.spinner("ML 모델들을 학습하고 있습니다..."):
                    try:
                        trainer = st.session_state.ml_trainer
                        X = st.session_state.preprocessed_X
                        y = st.session_state.preprocessed_y
                        
                        # 실시간 로그 표시를 위한 컨테이너
                        log_container = st.empty()
                        
                        # 표준출력 캡처를 위한 임시 방법
                        import sys
                        from io import StringIO
                        
                        old_stdout = sys.stdout
                        sys.stdout = captured_output = StringIO()
                        
                        try:
                            results = trainer.train_models(X, y)
                            
                            # 캡처된 출력 가져오기
                            output = captured_output.getvalue()
                            sys.stdout = old_stdout
                            
                            # 로그 표시
                            with log_container.expander("📋 학습 상세 로그", expanded=True):
                                st.code(output)
                                
                        except Exception as model_error:
                            sys.stdout = old_stdout
                            raise model_error
                        
                        # 결과 저장
                        st.session_state.project_data['initial_ml_results'] = results
                        st.session_state.project_data['best_score'] = trainer.best_score
                        st.session_state.ml_training_step = 2
                        
                        st.success("✅ 모델 학습 완료!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"학습 중 오류: {str(e)}")
        
        with col3:
            if st.button("3️⃣ 결과 저장", disabled=st.session_state.ml_training_step != 2):
                with st.spinner("학습 결과를 저장하고 있습니다..."):
                    try:
                        trainer = st.session_state.ml_trainer
                        
                        # 1. 초기 데이터를 파일로 저장
                        self.save_initial_training_data(df)
                        
                        # 2. 초기 모델 저장
                        self.save_model(trainer, 0)  # cycle 0 = 초기 모델
                        
                        # 3. 학습 완료 플래그
                        st.session_state.project_data['initial_training_completed'] = True
                        st.session_state.ml_training_step = 3
                        
                        # 자동 저장
                        self.auto_save()
                        
                        st.success("✅ 초기 모델 학습이 완료되었습니다!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"저장 중 오류: {str(e)}")
        
        # 진행 상황 표시
        if st.session_state.ml_training_step > 0:
            progress_steps = ["데이터 전처리", "모델 학습", "결과 저장", "완료"]
            current_step = min(st.session_state.ml_training_step, 3)
            
            st.write("### 📈 학습 진행 상황")
            progress_cols = st.columns(4)
            
            for i, step_name in enumerate(progress_steps):
                with progress_cols[i]:
                    if i < current_step:
                        st.success(f"✅ {step_name}")
                    elif i == current_step:
                        st.info(f"🔄 {step_name}")
                    else:
                        st.write(f"⏳ {step_name}")
        
        # 학습 완료 후 결과 표시
        if st.session_state.ml_training_step == 3 or 'initial_ml_results' in st.session_state.project_data:
            st.write("### 🏆 최종 모델 성능")
            
            if 'initial_ml_results' in st.session_state.project_data:
                results = st.session_state.project_data['initial_ml_results']
                trainer = st.session_state.ml_trainer
                
                # 성능 비교 차트
                results_df = pd.DataFrame(list(results.items()), columns=['Model', 'R² Score'])
                results_df = results_df.sort_values('R² Score', ascending=False)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = px.bar(results_df, x='Model', y='R² Score', 
                               title="모델 성능 비교 (R² Score)",
                               color='R² Score',
                               color_continuous_scale='RdYlGn')
                    fig.add_hline(y=0, line_dash="dash", line_color="red", 
                                annotation_text="베이스라인 (R²=0)")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.metric("최고 성능 모델", trainer.best_model_name or "None")
                    st.metric("최고 R² Score", f"{trainer.best_score:.4f}")
                    
                    # 성능 해석
                    if trainer.best_score < 0:
                        st.error("🚨 모델 성능이 베이스라인보다 낮습니다")
                    elif trainer.best_score < 0.3:
                        st.warning("⚠️ 모델 성능이 낮습니다")
                    elif trainer.best_score < 0.7:
                        st.info("📊 보통 수준의 성능입니다")
                    else:
                        st.success("🎉 좋은 성능입니다!")
                
                # 상세 결과 테이블
                self.safe_dataframe_display(results_df)
                
                # 선형 모델 계수 해석 (선형 모델인 경우에만)
                if (trainer.best_model_name and 
                    any(model_type in trainer.best_model_name.lower() 
                        for model_type in ['linear', 'ridge', 'lasso', 'elastic'])):
                    
                    with st.expander("📊 선형 모델 계수 해석", expanded=True):
                        try:
                            # 실제 모델에서 계수 추출
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
                                    fig = px.bar(coef_df, x='Feature', y='Coefficient',
                                               title="특성별 회귀 계수",
                                               color='Coefficient',
                                               color_continuous_scale='RdBu_r')
                                    fig.update_xaxis(tickangle=45)
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                with col2:
                                    st.write("**계수 해석:**")
                                    st.write(f"절편: {intercept:.4f}")
                                    st.write("**중요 특성 Top 3:**")
                                    for i, (_, row) in enumerate(coef_df.head(3).iterrows()):
                                        direction = "↗️ 양의 영향" if row['Coefficient'] > 0 else "↘️ 음의 영향"
                                        st.write(f"{i+1}. {row['Feature']}: {direction}")
                                
                                # 계수 테이블
                                st.write("**전체 계수:**")
                                display_coef = coef_df[['Feature', 'Coefficient']].copy()
                                display_coef['Coefficient'] = display_coef['Coefficient'].round(4)
                                self.safe_dataframe_display(display_coef, hide_index=True)
                                
                            elif hasattr(trainer.best_model, 'named_steps'):
                                # Pipeline인 경우 (Polynomial regression 등)
                                if 'linear' in trainer.best_model.named_steps:
                                    linear_model = trainer.best_model.named_steps['linear']
                                    if hasattr(linear_model, 'coef_'):
                                        st.info("다항 회귀 모델의 계수는 복잡하여 간단히 표시하지 않습니다.")
                                        st.write(f"계수 개수: {len(linear_model.coef_)}개")
                                        st.write(f"절편: {getattr(linear_model, 'intercept_', 'N/A'):.4f}")
                                        
                        except Exception as e:
                            st.warning(f"계수 해석 중 오류: {str(e)}")
                
                # 성능 문제 진단
                with st.expander("🔍 성능 문제 진단", expanded=trainer.best_score < 0.3):
                    st.write("#### 가능한 원인 분석:")
                    
                    # 데이터 크기 문제
                    data_size = len(st.session_state.preprocessed_y)
                    feature_count = len(feature_columns)
                    
                    if data_size < 50:
                        st.error(f"🚨 **데이터 부족**: {data_size}개 샘플 (권장: 최소 50개)")
                    elif data_size < 100:
                        st.warning(f"⚠️ **데이터 부족**: {data_size}개 샘플 (권장: 100개 이상)")
                    else:
                        st.success(f"✅ **충분한 데이터**: {data_size}개 샘플")
                    
                    # 특성 개수 문제
                    ratio = data_size / feature_count if feature_count > 0 else 0
                    if ratio < 10:
                        st.error(f"🚨 **특성 대비 데이터 부족**: 샘플 {data_size}개 / 특성 {feature_count}개 = {ratio:.1f} (권장: 10 이상)")
                    elif ratio < 20:
                        st.warning(f"⚠️ **특성이 많음**: 비율 {ratio:.1f} (권장: 20 이상)")
                    else:
                        st.success(f"✅ **적절한 비율**: {ratio:.1f}")
                    
                    # 타겟 변수 분석
                    y_std = np.std(st.session_state.preprocessed_y)
                    y_mean = np.mean(st.session_state.preprocessed_y)
                    cv = y_std / y_mean if y_mean != 0 else float('inf')
                    
                    if y_std < 0.01:
                        st.error("🚨 **타겟 변수 분산 부족**: 값들이 너무 유사함")
                    elif cv < 0.1:
                        st.warning("⚠️ **낮은 변동성**: 예측하기 어려운 패턴")
                    else:
                        st.success("✅ **적절한 변동성**")
                    
                    # 범주형 변수 분석
                    categorical_issues = []
                    for feature in feature_columns:
                        if df[feature].dtype == 'object':
                            unique_count = df[feature].nunique()
                            if unique_count == len(df):
                                categorical_issues.append(f"{feature}: 모든 값이 고유함 (식별자 가능성)")
                            elif unique_count > len(df) * 0.8:
                                categorical_issues.append(f"{feature}: 범주가 너무 많음 ({unique_count}개)")
                    
                    if categorical_issues:
                        st.error("🚨 **범주형 변수 문제**:")
                        for issue in categorical_issues:
                            st.write(f"  - {issue}")
                    
                    # 개선 제안
                    st.write("#### 💡 성능 개선 제안:")
                    if data_size < 100:
                        st.write("1. **더 많은 데이터 수집** (현재의 2-3배)")
                    if feature_count > data_size / 10:
                        st.write("2. **특성 선택** (중요도가 낮은 특성 제거)")
                    if y_std < 0.01:
                        st.write("3. **타겟 변수 재검토** (더 변동성 있는 지표 사용)")
                    if trainer.best_score < 0:
                        st.write("4. **데이터 품질 검토** (이상값, 오류 데이터 확인)")
                        st.write("5. **특성 엔지니어링** (파생 변수 생성, 상호작용 항 추가)")
                    
                    # 선형 모델 특화 제안
                    if hasattr(trainer, 'current_model_strategy') and trainer.model_preference == 'linear_focused':
                        st.write("#### 🔸 선형 모델 특화 개선 방안:")
                        st.write("• **Ridge 회귀**: 다중공선성 문제가 있을 때 유용")
                        st.write("• **Lasso 회귀**: 자동 특성 선택 효과 (중요하지 않은 특성을 0으로)")
                        st.write("• **ElasticNet**: Ridge와 Lasso의 장점 결합")
                        st.write("• **다항 회귀**: 비선형 관계를 선형 모델로 포착")
                        st.write("• **특성 스케일링**: 이미 적용되었지만 정규화 방법 변경 고려")
                        
                        if trainer.best_score < 0.1:
                            st.write("📋 **현재 데이터에 추천하는 접근법:**")
                            st.write("1. 먼저 **단순 선형 회귀**로 기본 관계 확인")
                            st.write("2. **Ridge 회귀**로 과적합 방지")
                            st.write("3. **특성 상호작용 추가** (A×B 형태의 새로운 특성)")
                            st.write("4. **로그 변환** 등 타겟 변수 변환 고려")
        
        # 기존 학습 결과 표시
        if 'initial_ml_results' in st.session_state.project_data:
            st.write("### 현재 모델 성능")
            results = st.session_state.project_data['initial_ml_results']
            results_df = pd.DataFrame(list(results.items()), columns=['Model', 'R² Score'])
            results_df = results_df.sort_values('R² Score', ascending=False)
            self.safe_dataframe_display(results_df)
    
    def step_model_analysis(self):
        """ML 모델 예측 및 분석 (사이클 단계)"""
        cycle_num = st.session_state.current_cycle + 1
        st.header(f"사이클 {cycle_num}: ML 모델 예측 및 분석")
        
        if not st.session_state.project_data.get('initial_training_completed', False):
            st.warning("먼저 초기 ML 모델 학습을 완료해주세요.")
            return
        
        # 현재까지 학습된 데이터 정보 표시
        st.write("### 현재 ML 모델 상태")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 학습 샘플 수", len(st.session_state.all_training_data))
        with col2:
            st.metric("완료된 사이클", st.session_state.current_cycle)
        with col3:
            current_score = st.session_state.project_data.get('best_score', 0)
            st.metric("현재 모델 R² Score", f"{current_score:.4f}")
        
        # ML 모델 예측 분석
        st.write("### ML 모델 예측 분석")
        
        if not hasattr(st.session_state.ml_trainer, 'best_model') or st.session_state.ml_trainer.best_model is None:
            st.warning("ML 모델이 학습되지 않았습니다.")
            return
        
        # 모델 성능 분석
        st.write("#### 🎯 모델 성능 요약")
        model_info = {
            "최적 모델": st.session_state.ml_trainer.best_model_name,
            "R² Score": f"{st.session_state.ml_trainer.best_score:.4f}",
            "학습 특성 수": len(st.session_state.project_data['feature_columns']),
            "학습 샘플 수": len(st.session_state.all_training_data)
        }
        
        col1, col2 = st.columns(2)
        with col1:
            for key, value in list(model_info.items())[:2]:
                st.metric(key, value)
        with col2:
            for key, value in list(model_info.items())[2:]:
                st.metric(key, value)
        
        # 특성 중요도 분석 (가능한 경우)
        try:
            if hasattr(st.session_state.ml_trainer.best_model, 'feature_importances_'):
                st.write("#### 📊 특성 중요도")
                feature_names = st.session_state.project_data['feature_columns']
                importances = st.session_state.ml_trainer.best_model.feature_importances_
                
                # 특성 중요도 시각화
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=feature_names,
                    y=importances,
                    text=[f"{imp:.3f}" for imp in importances],
                    textposition='auto'
                ))
                fig.update_layout(
                    title="특성 중요도 분석",
                    xaxis_title="특성",
                    yaxis_title="중요도",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info("특성 중요도 분석을 사용할 수 없습니다.")
        
        # 개별 조건 예측 테스트
        st.write("#### 🧪 개별 조건 예측 테스트")
        st.info("실험 조건을 입력하면 ML 모델이 예상 발현량을 예측합니다.")
        
        # 🏆 전체 영역 최고 예측값 상위 조건들 표시
        st.write("#### 🏆 전체 영역 최고 예측 조건 Top 10")
        
        try:
            if hasattr(st.session_state.ml_trainer, 'feature_names') and st.session_state.ml_trainer.feature_names:
                # 그리드 서치로 최고 조건들 탐색
                top_conditions = self.find_top_predicted_conditions(st.session_state.ml_trainer, n_top=10)
                
                if top_conditions:
                    st.write("**전체 파라미터 공간에서 예상 발현량이 높은 조건들:**")
                    
                    # 결과를 DataFrame으로 변환
                    top_df = pd.DataFrame(top_conditions)
                    top_df = top_df.round(3)  # 소수점 3자리로 제한
                    
                    # 예상 발현량 순으로 정렬
                    if 'predicted_yield' in top_df.columns:
                        top_df = top_df.sort_values('predicted_yield', ascending=False)
                        top_df.index = range(1, len(top_df) + 1)  # 순위로 인덱스 변경
                    
                    self.safe_dataframe_display(top_df)
                else:
                    st.info("최고 예측 조건을 찾을 수 없습니다.")
            else:
                st.info("ML 모델이 아직 학습되지 않았습니다.")
        except Exception as e:
            st.error(f"최고 예측 조건 탐색 중 오류: {str(e)}")
        
        # 입력 폼 생성 - ML 모델에서 실제 사용된 특성명 사용
        df = st.session_state.all_training_data
        
        # ML 모델에서 실제 학습에 사용된 특성들 사용
        if hasattr(st.session_state.ml_trainer, 'feature_names') and st.session_state.ml_trainer.feature_names:
            feature_columns = st.session_state.ml_trainer.feature_names
            st.info(f"ML 모델에서 사용된 {len(feature_columns)}개 특성: {feature_columns}")
            
            # 디버깅: 실제 데이터와 비교
            available_in_data = [col for col in feature_columns if col in df.columns]
            missing_in_data = [col for col in feature_columns if col not in df.columns]
            
            if missing_in_data:
                st.warning(f"학습 데이터에 없는 특성: {missing_in_data}")
            if len(available_in_data) != len(feature_columns):
                st.error(f"특성 불일치 발견! 모델 특성: {len(feature_columns)}개, 데이터 특성: {len(available_in_data)}개")
        else:
            feature_columns = st.session_state.project_data['feature_columns']
            st.warning("ML 모델의 특성 정보를 찾을 수 없습니다. 저장된 특성 목록을 사용합니다.")
        
        test_conditions = {}
        col1, col2 = st.columns(2)
        
        for i, col in enumerate(feature_columns):
            with col1 if i % 2 == 0 else col2:
                if df[col].dtype in ['int64', 'float64']:
                    min_val = float(df[col].min())
                    max_val = float(df[col].max())
                    test_conditions[col] = st.number_input(
                        f"{col}",
                        min_value=min_val,
                        max_value=max_val,
                        value=(min_val + max_val) / 2,
                        key=f"test_{col}"
                    )
                else:
                    unique_values = df[col].unique().tolist()
                    test_conditions[col] = st.selectbox(
                        f"{col}",
                        options=unique_values,
                        key=f"test_{col}"
                    )
        
        if st.button("🔮 예측하기"):
            try:
                # 예측 수행 - 강화된 디버깅
                print(f"\n🔍 예측 디버깅 시작")
                print(f"입력된 조건: {test_conditions}")
                
                # 1단계: 초기 DataFrame 생성
                test_df = pd.DataFrame([test_conditions])
                print(f"1️⃣ 초기 test_df shape: {test_df.shape}")
                print(f"1️⃣ 초기 columns: {list(test_df.columns)}")
                
                # 2단계: ML 모델 특성 확인
                if hasattr(st.session_state.ml_trainer, 'feature_names') and st.session_state.ml_trainer.feature_names:
                    expected_features = st.session_state.ml_trainer.feature_names
                    print(f"2️⃣ ML 모델 예상 특성 ({len(expected_features)}개): {expected_features}")
                    
                    # 3단계: 특성 매칭 확인
                    current_features = set(test_df.columns)
                    expected_features_set = set(expected_features)
                    missing_features = expected_features_set - current_features
                    extra_features = current_features - expected_features_set
                    
                    if missing_features:
                        print(f"3️⃣ 누락된 특성 ({len(missing_features)}개): {missing_features}")
                        for feature in missing_features:
                            test_df[feature] = 0
                    
                    if extra_features:
                        print(f"3️⃣ 불필요한 특성 ({len(extra_features)}개): {extra_features}")
                    
                    # 4단계: 특성 순서 맞춤
                    test_df = test_df[expected_features]
                    print(f"4️⃣ 최종 test_df shape: {test_df.shape}")
                    print(f"4️⃣ 최종 columns: {list(test_df.columns)}")
                else:
                    print("⚠️ ML 모델 특성 정보를 찾을 수 없습니다!")
                
                # 5단계: 인코딩
                X_encoded = test_df.copy()
                print(f"5️⃣ 인코딩 시작 - shape: {X_encoded.shape}")
                
                for column in X_encoded.columns:
                    if column in st.session_state.ml_trainer.label_encoders:
                        le = st.session_state.ml_trainer.label_encoders[column]
                        original_value = X_encoded[column].iloc[0]
                        if original_value in le.classes_:
                            encoded_value = le.transform([original_value])[0]
                            X_encoded[column] = encoded_value
                            print(f"   📝 {column}: '{original_value}' → {encoded_value}")
                        else:
                            X_encoded[column] = 0
                            print(f"   ❓ {column}: '{original_value}' (미지의 값) → 0")
                    else:
                        print(f"   ✅ {column}: {X_encoded[column].iloc[0]} (수치형)")
                
                print(f"5️⃣ 인코딩 완료 - shape: {X_encoded.shape}")
                
                # 6단계: 스케일링
                print(f"6️⃣ 스케일링 시작")
                print(f"   스케일러 기대 특성 수: {X_encoded.shape[1]}")
                
                X_scaled = st.session_state.ml_trainer.scaler.transform(X_encoded)
                print(f"6️⃣ 스케일링 완료 - shape: {X_scaled.shape}")
                
                # 7단계: 예측
                print(f"7️⃣ 예측 시작")
                prediction = st.session_state.ml_trainer.best_model.predict(X_scaled)[0]
                print(f"7️⃣ 예측 완료 - 결과: {prediction:.3f}")
                print(f"🔍 예측 디버깅 완료\n")
                
                # 결과 표시
                st.success(f"🎯 **예상 단백질 발현량: {prediction:.2f} mg/L**")
                
                # 예측 결과 저장
                st.session_state.project_data[f'cycle_{cycle_num}_prediction_test'] = {
                    'conditions': test_conditions,
                    'predicted_yield': prediction
                }
                self.auto_save()
                
            except Exception as e:
                st.error(f"예측 중 오류 발생: {str(e)}")
        
        # ML 모델 분석 완료 표시
        st.success("✅ ML 모델 분석이 완료되었습니다. 다음 단계로 진행하세요.")
    
    def step_experiment_design(self):
        """실험 설계 (사이클 단계)"""
        cycle_num = st.session_state.current_cycle + 1
        st.header(f"사이클 {cycle_num}: 실험 설계")
        
        if not hasattr(st.session_state.ml_trainer, 'best_model') or st.session_state.ml_trainer.best_model is None:
            st.warning("먼저 ML 모델을 학습해주세요.")
            return
        
        # 실험 제안 개수 설정
        n_suggestions = st.number_input(
            "제안받을 실험 조건 수",
            min_value=1,
            max_value=20,
            value=5
        )
        
        if st.button("🔍 베이지안 최적화로 실험 조건 제안", key=f"suggest_cycle_{cycle_num}"):
            with st.spinner("베이지안 최적화를 통해 최적 실험 조건을 찾고 있습니다..."):
                try:
                    # 현재 데이터에서 범위 추정 - ML 모델에서 실제 사용된 특성 사용
                    df = st.session_state.all_training_data
                    
                    # ML 모델에서 실제 학습에 사용된 특성들 사용
                    if hasattr(st.session_state.ml_trainer, 'feature_names') and st.session_state.ml_trainer.feature_names:
                        feature_columns = st.session_state.ml_trainer.feature_names
                        st.info(f"베이지안 최적화에 {len(feature_columns)}개 특성 사용")
                    else:
                        feature_columns = st.session_state.project_data['feature_columns']
                        st.warning("ML 모델의 특성 정보를 찾을 수 없어 저장된 특성 목록을 사용합니다.")
                    
                    # 베이지안 옵티마이저 초기화
                    optimizer = BayesianOptimizer(st.session_state.ml_trainer)
                    
                    # 파라미터 범위 설정
                    bounds_dict = {}
                    categorical_dict = {}
                    
                    for col in feature_columns:
                        if df[col].dtype == 'object':
                            categorical_dict[col] = df[col].unique().tolist()
                        else:
                            bounds_dict[col] = (float(df[col].min()), float(df[col].max()))
                    
                    # 베이지안 최적화 설정
                    optimizer.set_bounds(bounds_dict)
                    optimizer.set_categorical_features(categorical_dict)
                    
                    # 베이지안 최적화로 실험 조건 제안
                    suggestions = optimizer.suggest_experiments(n_suggestions)
                    
                    st.session_state.project_data[f'cycle_{cycle_num}_experiment_suggestions'] = suggestions
                    
                    # 자동 저장
                    self.auto_save()
                    
                    st.success(f"🎯 베이지안 최적화를 통해 {n_suggestions}개의 최적 실험 조건이 제안되었습니다!")
                    
                except Exception as e:
                    st.error(f"실험 제안 중 오류 발생: {str(e)}")
        
        # 제안된 실험 조건 표시
        suggestions_key = f'cycle_{cycle_num}_experiment_suggestions'
        if suggestions_key in st.session_state.project_data:
            suggestions = st.session_state.project_data[suggestions_key]
            
            st.write("### 제안된 실험 조건들")
            suggestions_df = pd.DataFrame(suggestions)
            self.safe_dataframe_display(suggestions_df)
            
            # 실험 조건 선택
            st.write("### 실행할 실험 선택")
            selected_indices = st.multiselect(
                "실행할 실험을 선택하세요 (인덱스)",
                range(len(suggestions)),
                default=list(range(len(suggestions))),
                key=f"select_exp_cycle_{cycle_num}"
            )
            
            if selected_indices:
                selected_experiments = [suggestions[i] for i in selected_indices]
                st.session_state.project_data[f'cycle_{cycle_num}_selected_experiments'] = selected_experiments
                
                st.write(f"**선택된 실험 수:** {len(selected_experiments)}")
                selected_df = pd.DataFrame(selected_experiments)
                self.safe_dataframe_display(selected_df)
                
                # 추가 실험 조건 수동 입력
                st.write("### 추가 실험 조건 (선택사항)")
                
                additional_key = f'cycle_{cycle_num}_additional_experiments'
                if additional_key not in st.session_state:
                    st.session_state[additional_key] = []
                
                # 새 실험 조건 추가 폼
                with st.expander("새 실험 조건 추가"):
                    feature_columns = st.session_state.project_data['feature_columns']
                    new_experiment = {}
                    
                    for col in feature_columns:
                        if col in suggestions_df.columns:
                            if suggestions_df[col].dtype == 'object':
                                unique_vals = suggestions_df[col].unique()
                                new_experiment[col] = st.selectbox(f"{col} 선택", unique_vals, key=f"add_{col}")
                            else:
                                min_val = suggestions_df[col].min()
                                max_val = suggestions_df[col].max()
                                new_experiment[col] = st.number_input(
                                    f"{col} 값",
                                    min_value=float(min_val),
                                    max_value=float(max_val),
                                    value=float((min_val + max_val) / 2),
                                    key=f"add_{col}"
                                )
                    
                    if st.button("추가 실험 조건 저장", key=f"save_additional_cycle_{cycle_num}"):
                        st.session_state[additional_key].append(new_experiment)
                        st.success("추가 실험 조건이 저장되었습니다!")
                        st.rerun()
                
                # 추가된 실험 조건 표시
                if st.session_state[additional_key]:
                    st.write("### 추가된 실험 조건들")
                    additional_df = pd.DataFrame(st.session_state[additional_key])
                    self.safe_dataframe_display(additional_df)
                    
                    # 전체 실험 목록 업데이트
                    all_experiments = selected_experiments + st.session_state[additional_key]
                    st.session_state.project_data[f'cycle_{cycle_num}_final_experiments'] = all_experiments
    
    def step_mapping_generation(self):
        """매핑 파일 생성 (사이클 단계)"""
        cycle_num = st.session_state.current_cycle + 1
        st.header(f"사이클 {cycle_num}: 매핑 파일 생성")
        
        selected_exp_key = f'cycle_{cycle_num}_selected_experiments'
        if selected_exp_key not in st.session_state.project_data:
            st.warning("먼저 실험을 설계해주세요.")
            return
        
        final_exp_key = f'cycle_{cycle_num}_final_experiments'
        experiments = st.session_state.project_data.get(final_exp_key, 
                                                      st.session_state.project_data[selected_exp_key])
        
        st.write(f"### 총 {len(experiments)}개 실험에 대한 매핑 파일 생성")
        
        # 플레이트 설정
        col1, col2 = st.columns(2)
        
        with col1:
            plate_type = st.selectbox("플레이트 타입", [96, 384], index=0)
            
        with col2:
            replicate_count = st.number_input("복제 실험 수", min_value=1, max_value=5, value=1)
        
        # 실험 복제 처리
        if replicate_count > 1:
            replicated_experiments = []
            for i, exp in enumerate(experiments):
                for rep in range(replicate_count):
                    exp_copy = exp.copy()
                    exp_copy['Original_Index'] = i
                    exp_copy['Replicate'] = rep + 1
                    replicated_experiments.append(exp_copy)
            final_experiments = replicated_experiments
        else:
            final_experiments = experiments
        
        st.write(f"**복제 포함 총 실험 수:** {len(final_experiments)}")
        
        # 매핑 파일 생성
        if st.button("매핑 파일 생성", key=f"generate_mapping_cycle_{cycle_num}"):
            try:
                generator = st.session_state.mapping_generator
                
                # 매핑 데이터프레임 생성
                mapping_df = generator.create_mapping_file(
                    final_experiments, 
                    plate_type=plate_type
                )
                
                # 프로토콜 파일 생성
                protocol_df = generator.create_protocol_file(mapping_df)
                
                # 플레이트 시각화 데이터 생성
                plate_visualization_df = generator.create_plate_visualization(mapping_df)
                
                # 결과 저장 (사이클별로)
                st.session_state.project_data[f'cycle_{cycle_num}_mapping_df'] = mapping_df
                st.session_state.project_data[f'cycle_{cycle_num}_protocol_df'] = protocol_df
                st.session_state.project_data[f'cycle_{cycle_num}_plate_visualization'] = plate_visualization_df
                
                # 자동 저장
                self.auto_save()
                
                st.success("매핑 파일이 생성되었습니다!")
                
            except Exception as e:
                st.error(f"매핑 파일 생성 중 오류 발생: {str(e)}")
        
        # 생성된 파일들 표시 및 다운로드
        mapping_key = f'cycle_{cycle_num}_mapping_df'
        protocol_key = f'cycle_{cycle_num}_protocol_df'
        
        if mapping_key in st.session_state.project_data:
            mapping_df = st.session_state.project_data[mapping_key]
            protocol_df = st.session_state.project_data[protocol_key]
            
            # 탭으로 구분
            tab1, tab2, tab3 = st.tabs(["매핑 파일", "프로토콜 파일", "플레이트 레이아웃"])
            
            with tab1:
                st.write("### 매핑 파일")
                self.safe_dataframe_display(mapping_df)
                
                # CSV 다운로드
                csv_mapping = mapping_df.to_csv(index=False)
                st.download_button(
                    label="매핑 파일 다운로드 (CSV)",
                    data=csv_mapping,
                    file_name=f"{st.session_state.project_data.get('project_name', 'project')}_cycle_{cycle_num}_mapping.csv",
                    mime="text/csv",
                    key=f"download_mapping_cycle_{cycle_num}"
                )
            
            with tab2:
                st.write("### 프로토콜 파일")
                self.safe_dataframe_display(protocol_df)
                
                # CSV 다운로드
                csv_protocol = protocol_df.to_csv(index=False)
                st.download_button(
                    label="프로토콜 파일 다운로드 (CSV)",
                    data=csv_protocol,
                    file_name=f"{st.session_state.project_data.get('project_name', 'project')}_cycle_{cycle_num}_protocol.csv",
                    mime="text/csv",
                    key=f"download_protocol_cycle_{cycle_num}"
                )
            
            with tab3:
                st.write("### 플레이트 레이아웃 시각화")
                
                # 플레이트 시각화 데이터 가져오기
                plate_key = f'cycle_{cycle_num}_plate_visualization'
                if plate_key in st.session_state.project_data:
                    plate_viz_df = pd.DataFrame(st.session_state.project_data[plate_key])
                    self.visualize_plate_layout_advanced(plate_viz_df, plate_type)
                else:
                    self.visualize_plate_layout(mapping_df, plate_type)
    
    def visualize_plate_layout(self, mapping_df, plate_type):
        """플레이트 레이아웃 시각화"""
        if plate_type == 96:
            rows, cols = 8, 12
        else:  # 384
            rows, cols = 16, 24
        
        # 플레이트 격자 생성
        plate_grid = np.full((rows, cols), "", dtype=object)
        
        for _, row in mapping_df.iterrows():
            well = row['Well']
            row_idx = ord(well[0]) - ord('A')
            col_idx = int(well[1:]) - 1
            
            if row_idx < rows and col_idx < cols:
                plate_grid[row_idx, col_idx] = row['Sample_ID']
        
        # 히트맵 생성
        fig = go.Figure(data=go.Heatmap(
            z=np.arange(rows * cols).reshape(rows, cols),
            text=plate_grid,
            texttemplate="%{text}",
            textfont={"size": 8},
            colorscale='Viridis',
            showscale=False
        ))
        
        # 축 레이블 설정
        row_labels = [chr(ord('A') + i) for i in range(rows)]
        col_labels = [str(i+1) for i in range(cols)]
        
        fig.update_layout(
            title=f"{plate_type}-well 플레이트 레이아웃",
            xaxis=dict(tickvals=list(range(cols)), ticktext=col_labels),
            yaxis=dict(tickvals=list(range(rows)), ticktext=row_labels),
            width=800,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def visualize_plate_layout_advanced(self, plate_viz_df, plate_type):
        """고급 플레이트 레이아웃 시각화"""
        
        # 플레이트 설정
        if plate_type == '384-well':
            rows, cols = 16, 24
        else:
            rows, cols = 8, 12
        
        # 플레이트 그리드 생성
        plate_matrix = np.zeros((rows, cols))
        text_matrix = np.full((rows, cols), "", dtype=object)
        
        for _, row in plate_viz_df.iterrows():
            row_idx = ord(row['Row']) - ord('A')
            col_idx = row['Column'] - 1
            
            if row['Status'] == 'Used':
                plate_matrix[row_idx, col_idx] = 1
                text_matrix[row_idx, col_idx] = row['Sample_ID']
            else:
                plate_matrix[row_idx, col_idx] = 0
                text_matrix[row_idx, col_idx] = ""
        
        # 인터랙티브 히트맵 생성
        fig = go.Figure(data=go.Heatmap(
            z=plate_matrix,
            text=text_matrix,
            texttemplate="%{text}",
            textfont={"size": 10 if plate_type == '96-well' else 6},
            colorscale=[[0, '#f0f0f0'], [1, '#2E86C1']],
            showscale=False,
            hovertemplate='<b>Well:</b> %{y}%{x}<br>' +
                         '<b>Sample:</b> %{text}<br>' +
                         '<b>Status:</b> %{customdata}<extra></extra>',
            customdata=plate_viz_df.pivot(index='Row', columns='Column', values='Status').values
        ))
        
        # 축 레이블 설정
        row_labels = [chr(ord('A') + i) for i in range(rows)]
        col_labels = [str(i+1) for i in range(cols)]
        
        fig.update_layout(
            title=f"{plate_type} 플레이트 레이아웃 - 사용된 Well: {len(plate_viz_df[plate_viz_df['Status'] == 'Used'])}개",
            xaxis=dict(
                tickvals=list(range(cols)), 
                ticktext=col_labels,
                side='top'
            ),
            yaxis=dict(
                tickvals=list(range(rows)), 
                ticktext=row_labels,
                autorange='reversed'
            ),
            width=900 if plate_type == '96-well' else 1200,
            height=500 if plate_type == '96-well' else 800,
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 통계 정보 표시
        used_wells = len(plate_viz_df[plate_viz_df['Status'] == 'Used'])
        total_wells = rows * cols
        usage_percentage = (used_wells / total_wells) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("사용된 Well 수", used_wells)
        with col2:
            st.metric("전체 Well 수", total_wells)
        with col3:
            st.metric("사용률", f"{usage_percentage:.1f}%")
    
    def step_results_analysis(self):
        """7단계: 결과 분석"""
        st.header("7. 결과 분석 및 프로젝트 요약")
        
        # 프로젝트 요약
        st.write("### 프로젝트 요약")
        
        if st.session_state.project_data:
            summary_data = {
                "항목": [
                    "프로젝트 이름",
                    "실험 유형",
                    "초기 데이터 샘플 수",
                    "최고 모델 성능 (R²)",
                    "최적화된 예측값",
                    "최종 실험 설계 수",
                    "생성된 매핑 파일"
                ],
                "값": [
                    st.session_state.project_data.get('project_name', 'N/A'),
                    st.session_state.project_data.get('experiment_type', 'N/A'),
                    len(st.session_state.project_data.get('initial_data', [])),
                    f"{st.session_state.project_data.get('best_score', 0):.4f}",
                    f"{st.session_state.project_data.get('optimization_results', {}).get('best_value', 0):.4f}",
                    len(st.session_state.project_data.get('final_experiments', [])),
                    "생성됨" if 'mapping_df' in st.session_state.project_data else "미생성"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, hide_index=True)
        
        # 결과 업로드 섹션
        st.write("### 실험 결과 업로드 및 분석")
        
        uploaded_results = st.file_uploader(
            "실험 결과 파일을 업로드하세요 (CSV 또는 Excel)",
            type=['csv', 'xlsx', 'xls']
        )
        
        if uploaded_results is not None:
            try:
                if uploaded_results.name.endswith('.csv'):
                    results_df = pd.read_csv(uploaded_results)
                else:
                    results_df = pd.read_excel(uploaded_results)
                
                st.write("### 실험 결과 데이터")
                st.dataframe(results_df)
                
                # 결과 분석
                if st.session_state.project_data.get('target_column') in results_df.columns:
                    target_col = st.session_state.project_data['target_column']
                    
                    # 기본 통계
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**결과 통계:**")
                        st.write(results_df[target_col].describe())
                    
                    with col2:
                        # 최고/최저 성능 실험
                        best_idx = results_df[target_col].idxmax()
                        worst_idx = results_df[target_col].idxmin()
                        
                        st.write("**최고 성능 실험:**")
                        st.write(f"값: {results_df.loc[best_idx, target_col]}")
                        
                        st.write("**최저 성능 실험:**")
                        st.write(f"값: {results_df.loc[worst_idx, target_col]}")
                    
                    # 결과 시각화
                    fig = px.histogram(results_df, x=target_col, 
                                     title=f"{target_col} 결과 분포")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 예측 vs 실제 (모델이 있는 경우)
                    if 'ml_trainer' in st.session_state and st.session_state.ml_trainer.best_model:
                        st.write("### 예측 성능 평가")
                        
                        try:
                            # 특성 변수만 추출
                            feature_cols = st.session_state.project_data.get('feature_columns', [])
                            X_test = results_df[feature_cols]
                            
                            # 예측
                            predictions = st.session_state.ml_trainer.predict(X_test.values)
                            
                            # 예측 vs 실제 플롯
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=results_df[target_col],
                                y=predictions,
                                mode='markers',
                                name='예측 vs 실제'
                            ))
                            
                            # 대각선 추가
                            min_val = min(results_df[target_col].min(), predictions.min())
                            max_val = max(results_df[target_col].max(), predictions.max())
                            fig.add_trace(go.Scatter(
                                x=[min_val, max_val],
                                y=[min_val, max_val],
                                mode='lines',
                                name='이상적 예측',
                                line=dict(dash='dash')
                            ))
                            
                            fig.update_layout(
                                title="예측값 vs 실제값",
                                xaxis_title="실제값",
                                yaxis_title="예측값"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # 성능 지표
                            mse = mean_squared_error(results_df[target_col], predictions)
                            r2 = r2_score(results_df[target_col], predictions)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("평균 제곱 오차 (MSE)", f"{mse:.4f}")
                            with col2:
                                st.metric("결정 계수 (R²)", f"{r2:.4f}")
                                
                        except Exception as e:
                            st.error(f"예측 성능 평가 중 오류: {str(e)}")
                
            except Exception as e:
                st.error(f"결과 파일 읽기 오류: {str(e)}")
        
        # 프로젝트 데이터 내보내기
        st.write("### 프로젝트 데이터 내보내기")
        
        if st.button("전체 프로젝트 데이터 내보내기 (JSON)"):
            project_export = st.session_state.project_data.copy()
            
            # DataFrame을 딕셔너리로 변환
            for key, value in project_export.items():
                if isinstance(value, pd.DataFrame):
                    project_export[key] = value.to_dict('records')
            
            project_json = json.dumps(project_export, indent=2, default=str)
            
            st.download_button(
                label="프로젝트 데이터 다운로드 (JSON)",
                data=project_json,
                file_name=f"{st.session_state.project_data.get('project_name', 'project')}_data.json",
                mime="application/json"
            )
    
    def step_result_input_and_model_update(self):
        """결과 입력 및 모델 업데이트 (사이클 단계)"""
        cycle_num = st.session_state.current_cycle + 1
        st.header(f"사이클 {cycle_num}: 실험 결과 입력 및 모델 업데이트")
        
        # 현재 사이클의 매핑 파일이 있는지 확인
        mapping_key = f'cycle_{cycle_num}_mapping_df'
        if mapping_key not in st.session_state.project_data:
            st.warning("먼저 매핑 파일을 생성해주세요.")
            return
        
        mapping_df = st.session_state.project_data[mapping_key]
        
        st.write("### 실험 결과 입력")
        st.write(f"**사이클 {cycle_num}에서 생성된 실험 조건 수:** {len(mapping_df)}")
        
        # 결과 입력 방법 선택
        input_method = st.radio(
            "결과 입력 방법을 선택하세요:",
            ["파일 업로드", "수동 입력", "테스트 데이터 생성"]
        )
        
        new_results = None
        
        if input_method == "파일 업로드":
            uploaded_file = st.file_uploader(
                "실험 결과 파일을 업로드하세요 (CSV 또는 Excel)",
                type=['csv', 'xlsx', 'xls'],
                key=f"cycle_{cycle_num}_upload"
            )
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        results_df = pd.read_csv(uploaded_file)
                    else:
                        results_df = pd.read_excel(uploaded_file)
                    
                    st.write("### 업로드된 결과 데이터")
                    self.safe_dataframe_display(results_df)
                    
                    # 타겟 컬럼 확인
                    target_column = st.session_state.project_data['target_column']
                    if target_column in results_df.columns:
                        new_results = results_df
                        st.success(f"결과 데이터가 성공적으로 로드되었습니다. ({len(results_df)}개 샘플)")
                    else:
                        st.error(f"타겟 컬럼 '{target_column}'이 결과 데이터에 없습니다.")
                        
                except Exception as e:
                    st.error(f"파일 읽기 오류: {str(e)}")
        
        elif input_method == "수동 입력":
            st.write("### 수동 결과 입력")
            
            # 매핑 파일 기반으로 입력 폼 생성
            target_column = st.session_state.project_data['target_column']
            
            with st.expander("실험 결과 입력 폼", expanded=True):
                results_data = []
                
                for idx, row in mapping_df.iterrows():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**{row['Sample_ID']}**: {dict(row.drop(['Well', 'Sample_ID']))}")
                    
                    with col2:
                        result_value = st.number_input(
                            f"{target_column}",
                            value=0.0,
                            key=f"result_{cycle_num}_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        # 결과 데이터에 추가
                        result_row = row.copy()
                        result_row[target_column] = result_value
                        results_data.append(result_row)
                
                if st.button(f"사이클 {cycle_num} 결과 확인", key=f"confirm_results_{cycle_num}"):
                    new_results = pd.DataFrame(results_data)
                    st.success("결과가 입력되었습니다!")
        
        elif input_method == "테스트 데이터 생성":
            st.write("### 테스트 데이터 자동 생성")
            st.info("실제 실험을 하지 않고도 시스템을 테스트할 수 있는 가상의 실험 결과를 생성합니다.")
            
            # 테스트 데이터 생성 파라미터
            col1, col2 = st.columns(2)
            
            with col1:
                noise_level = st.slider(
                    "노이즈 레벨", 
                    min_value=0.1, 
                    max_value=0.5, 
                    value=0.2, 
                    step=0.05,
                    help="높을수록 더 많은 랜덤 변동 추가"
                )
            
            with col2:
                performance_trend = st.selectbox(
                    "성능 트렌드",
                    ["개선", "유지", "악화"],
                    help="이전 사이클 대비 전반적인 성능 변화"
                )
            
            if st.button(f"사이클 {cycle_num} 테스트 데이터 생성", key=f"generate_test_data_{cycle_num}"):
                try:
                    # 베이지안 최적화 결과 반영
                    target_column = st.session_state.project_data['target_column']
                    
                    # 현재까지의 최고 성능 확인
                    if len(st.session_state.all_training_data) > 0:
                        current_best = st.session_state.all_training_data[target_column].max()
                    else:
                        current_best = 100
                    
                    # 성능 트렌드에 따른 조정
                    trend_multiplier = {"개선": 1.1, "유지": 1.0, "악화": 0.9}[performance_trend]
                    
                    # 테스트 데이터 생성
                    test_results = generate_test_experiment_results(
                        mapping_df, 
                        target_column
                    )
                    
                    # 성능 트렌드 적용
                    test_results[target_column] = test_results[target_column] * trend_multiplier
                    
                    # 노이즈 추가
                    noise = np.random.normal(0, test_results[target_column].std() * noise_level, len(test_results))
                    test_results[target_column] += noise
                    
                    # 음수값 방지
                    test_results[target_column] = np.maximum(test_results[target_column], 10)
                    
                    # 소수점 1자리로 반올림
                    test_results[target_column] = np.round(test_results[target_column], 1)
                    
                    new_results = test_results
                    
                    st.success("테스트 데이터가 생성되었습니다!")
                    st.write("### 생성된 테스트 결과")
                    self.safe_dataframe_display(test_results)
                    
                    # 통계 정보
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("평균", f"{test_results[target_column].mean():.2f}")
                    with col2:
                        st.metric("최대값", f"{test_results[target_column].max():.2f}")
                    with col3:
                        st.metric("최소값", f"{test_results[target_column].min():.2f}")
                    with col4:
                        st.metric("표준편차", f"{test_results[target_column].std():.2f}")
                    
                except Exception as e:
                    st.error(f"테스트 데이터 생성 중 오류: {str(e)}")
        
        # 결과가 입력되었으면 모델 업데이트
        if new_results is not None:
            st.write("### 모델 업데이트")
            
            if st.button(f"사이클 {cycle_num} 데이터로 모델 업데이트", key=f"update_model_{cycle_num}"):
                with st.spinner("모델을 업데이트하고 있습니다..."):
                    try:
                        # ml_trainer 확인 및 초기화
                        if 'ml_trainer' not in st.session_state or st.session_state.ml_trainer is None:
                            st.session_state.ml_trainer = MLModelTrainer(model_preference='linear_focused', encoding_method='auto', target_transform='auto')
                        
                        # all_training_data 확인 및 초기화
                        if 'all_training_data' not in st.session_state or st.session_state.all_training_data is None:
                            # 초기 데이터부터 다시 로드
                            initial_data = pd.DataFrame(st.session_state.project_data['initial_data'])
                            st.session_state.all_training_data = initial_data.copy()
                        
                        # 1. 사이클별 결과 데이터 파일로 저장
                        self.save_cycle_data(cycle_num, new_results)
                        
                        # 2. 누적 학습 데이터 업데이트 및 저장
                        updated_training_data = self.update_training_data(new_results)
                        
                        # 3. 저장된 데이터로 모델 재학습
                        trainer = st.session_state.ml_trainer
                        target_column = st.session_state.project_data['target_column']
                        
                        feature_columns = st.session_state.project_data.get('feature_columns', None)
                        X, y = trainer.preprocess_data(updated_training_data, target_column, feature_columns)
                        results = trainer.train_models(X, y)
                        
                        # 4. 모델 저장
                        self.save_model(trainer, cycle_num)
                        
                        # 5. 결과 저장
                        st.session_state.project_data[f'cycle_{cycle_num}_results'] = new_results.to_dict('records')
                        st.session_state.project_data['best_score'] = trainer.best_score
                        st.session_state.project_data[f'cycle_{cycle_num}_model_results'] = results
                        
                        # 6. 프로젝트 상태 저장
                        self.auto_save()
                        
                        st.success(f"사이클 {cycle_num} 완료! 모델이 업데이트되었습니다.")
                        
                        # 성능 비교 표시
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("업데이트된 모델 R² Score", f"{trainer.best_score:.4f}")
                        
                        with col2:
                            st.metric("총 학습 데이터 수", len(st.session_state.all_training_data))
                        
                        # 성능 개선 그래프
                        self.plot_model_performance_over_cycles()
                        
                        # 다음 사이클 진행 옵션
                        st.write("---")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("🔄 다음 사이클 시작", key=f"next_cycle_{cycle_num}", type="primary"):
                                st.session_state.current_cycle += 1
                                st.session_state.current_step = 4  # 모델 분석 단계로
                                self.auto_save()
                                st.rerun()
                        
                        with col2:
                            if st.button("🏁 프로젝트 완료", key=f"finish_project_{cycle_num}"):
                                st.session_state.current_step = 5  # 프로젝트 완료 단계로
                                self.auto_save()
                                st.rerun()
                        
                    except Exception as e:
                        st.error(f"모델 업데이트 중 오류 발생: {str(e)}")
                        
                        # 디버깅 정보 표시
                        with st.expander("디버깅 정보"):
                            st.write("**Session State 확인:**")
                            st.write(f"- ml_trainer 존재: {'ml_trainer' in st.session_state}")
                            st.write(f"- all_training_data 타입: {type(st.session_state.get('all_training_data'))}")
                            if 'all_training_data' in st.session_state:
                                st.write(f"- all_training_data 크기: {len(st.session_state.all_training_data) if st.session_state.all_training_data is not None else 'None'}")
                            st.write(f"- target_column: {st.session_state.project_data.get('target_column')}")
                            st.write(f"- new_results 크기: {len(new_results) if new_results is not None else 'None'}")
                            
                            import traceback
                            st.code(traceback.format_exc())
        
        # 사이클 데이터가 있으면 표시
        if f'cycle_{cycle_num}_results' in st.session_state.project_data:
            cycle_results = pd.DataFrame(st.session_state.project_data[f'cycle_{cycle_num}_results'])
            
            st.write("### 현재 사이클 결과")
            self.safe_dataframe_display(cycle_results)
            
            # 통계 정보
            target_column = st.session_state.project_data['target_column']
            if target_column in cycle_results.columns:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("평균", f"{cycle_results[target_column].mean():.2f}")
                with col2:
                    st.metric("최대값", f"{cycle_results[target_column].max():.2f}")
                with col3:
                    st.metric("최소값", f"{cycle_results[target_column].min():.2f}")
                with col4:
                    st.metric("표준편차", f"{cycle_results[target_column].std():.2f}")
    
    def plot_model_performance_over_cycles(self):
        """사이클별 모델 성능 변화 그래프"""
        st.write("### 사이클별 모델 성능 변화")
        
        # 초기 성능
        performance_data = []
        if 'best_score' in st.session_state.project_data:
            performance_data.append({
                'Cycle': 'Initial',
                'R2_Score': st.session_state.project_data.get('best_score', 0),
                'Data_Count': len(st.session_state.project_data.get('initial_data', []))
            })
        
        # 각 사이클 성능
        for cycle in range(1, st.session_state.current_cycle + 2):  # +2 because we want to include current cycle
            model_results_key = f'cycle_{cycle}_model_results'
            if model_results_key in st.session_state.project_data:
                # Get the best score from the cycle's model results
                cycle_results = st.session_state.project_data[model_results_key]
                if isinstance(cycle_results, dict):
                    best_score = max(cycle_results.values()) if cycle_results else 0
                else:
                    best_score = 0
                
                performance_data.append({
                    'Cycle': f'Cycle {cycle}',
                    'R2_Score': best_score,
                    'Data_Count': len(st.session_state.all_training_data)
                })
        
        if len(performance_data) > 1:
            perf_df = pd.DataFrame(performance_data)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=perf_df['Cycle'],
                y=perf_df['R2_Score'],
                mode='lines+markers',
                name='R² Score',
                line=dict(color='blue', width=3),
                marker=dict(size=10)
            ))
            
            fig.update_layout(
                title="사이클별 모델 성능 개선",
                xaxis_title="사이클",
                yaxis_title="R² Score",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def run_step(self):
        """현재 단계 실행"""
        # 고정 단계들
        fixed_step_functions = [
            self.step_project_setup,
            self.step_initial_data_input,
            self.step_initial_ml_training
        ]
        
        # 사이클 단계들
        cycle_step_functions = [
            self.step_model_analysis,
            self.step_experiment_design,
            self.step_mapping_generation,
            self.step_result_input_and_model_update
        ]
        
        current_step = st.session_state.current_step
        
        # 고정 단계 실행
        if current_step < len(fixed_step_functions):
            fixed_step_functions[current_step]()
        
        # 사이클 단계 실행
        elif st.session_state.in_cycle_phase:
            cycle_step_index = current_step - len(fixed_step_functions)
            if 0 <= cycle_step_index < len(cycle_step_functions):
                cycle_step_functions[cycle_step_index]()
        
        # 프로젝트 종료 단계
        else:
            self.step_project_summary()
    
    def step_project_summary(self):
        """프로젝트 최종 요약"""
        st.header("프로젝트 완료 및 전체 요약")
        
        # 전체 프로젝트 통계
        st.write("### 프로젝트 전체 통계")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("완료된 사이클 수", st.session_state.current_cycle)
        with col2:
            st.metric("총 실험 데이터 수", len(st.session_state.all_training_data))
        with col3:
            initial_score = 0
            if 'initial_ml_results' in st.session_state.project_data:
                initial_results = st.session_state.project_data['initial_ml_results']
                initial_score = max(initial_results.values()) if initial_results else 0
            st.metric("초기 모델 성능", f"{initial_score:.4f}")
        with col4:
            final_score = st.session_state.project_data.get('best_score', 0)
            st.metric("최종 모델 성능", f"{final_score:.4f}")
        
        # 성능 개선 그래프
        if st.session_state.current_cycle > 0:
            self.plot_model_performance_over_cycles()
        
        # 전체 데이터 요약
        st.write("### 전체 실험 데이터")
        if len(st.session_state.all_training_data) > 0:
            self.safe_dataframe_display(st.session_state.all_training_data)
            
            # 타겟 변수 분포
            target_column = st.session_state.project_data['target_column']
            fig = px.histogram(
                st.session_state.all_training_data, 
                x=target_column,
                title=f"전체 {target_column} 분포"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 사이클별 결과 요약
        st.write("### 사이클별 결과 요약")
        
        cycle_summary = []
        for cycle in range(1, st.session_state.current_cycle + 1):
            cycle_key = f'cycle_{cycle}_results'
            if cycle_key in st.session_state.project_data:
                cycle_data = pd.DataFrame(st.session_state.project_data[cycle_key])
                target_column = st.session_state.project_data['target_column']
                
                if target_column in cycle_data.columns:
                    cycle_summary.append({
                        'Cycle': cycle,
                        'Experiments': len(cycle_data),
                        'Mean_Value': cycle_data[target_column].mean(),
                        'Max_Value': cycle_data[target_column].max(),
                        'Min_Value': cycle_data[target_column].min(),
                        'Std_Value': cycle_data[target_column].std()
                    })
        
        if cycle_summary:
            summary_df = pd.DataFrame(cycle_summary)
            self.safe_dataframe_display(summary_df)
        
        # 데이터 내보내기
        st.write("### 데이터 내보내기")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("전체 실험 데이터 다운로드 (CSV)"):
                csv_data = st.session_state.all_training_data.to_csv(index=False)
                st.download_button(
                    label="CSV 다운로드",
                    data=csv_data,
                    file_name=f"{st.session_state.project_data.get('project_name', 'project')}_all_data.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("프로젝트 설정 다운로드 (JSON)"):
                project_export = st.session_state.project_data.copy()
                
                # DataFrame을 딕셔너리로 변환
                for key, value in project_export.items():
                    if isinstance(value, pd.DataFrame):
                        project_export[key] = value.to_dict('records')
                
                project_json = json.dumps(project_export, indent=2, default=str)
                
                st.download_button(
                    label="JSON 다운로드",
                    data=project_json,
                    file_name=f"{st.session_state.project_data.get('project_name', 'project')}_config.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("새 프로젝트 시작"):
                # 세션 상태 초기화
                for key in list(st.session_state.keys()):
                    if key.startswith(('project_data', 'current_', 'in_cycle', 'ml_trainer', 'all_training_data', 'cycle_data')):
                        del st.session_state[key]
                st.rerun()
    
    def load_project(self, project_safe_name: str):
        """프로젝트 로드"""
        try:
            # 현재 프로젝트 저장 (다른 프로젝트로 전환하는 경우)
            if st.session_state.current_project and st.session_state.current_project != project_safe_name:
                self.save_current_project()
            
            # 프로젝트 데이터 로드
            project_data = st.session_state.data_manager.load_project(project_safe_name)
            
            # 세션 상태 업데이트
            st.session_state.current_project = project_safe_name
            st.session_state.current_step = project_data['config'].get('current_step', 0)
            st.session_state.current_cycle = project_data['config'].get('current_cycle', 0)
            st.session_state.in_cycle_phase = project_data['config'].get('in_cycle_phase', False)
            
            # 프로젝트 데이터 복원
            st.session_state.project_data = project_data['project_data']
            
            # DataFrame 데이터 복원
            for key, value in st.session_state.project_data.items():
                if isinstance(value, dict) and value.get('type') == 'dataframe':
                    st.session_state.project_data[key] = pd.DataFrame(value['data'])
            
            # 파일에서 누적 학습 데이터 로드
            loaded_training_data = self.load_training_data()
            if not loaded_training_data.empty:
                st.session_state.all_training_data = loaded_training_data
            elif project_data['all_training_data'] is not None and not project_data['all_training_data'].empty:
                st.session_state.all_training_data = project_data['all_training_data']
            else:
                # 초기 데이터가 있으면 그것으로 시작
                if 'initial_data' in st.session_state.project_data:
                    st.session_state.all_training_data = pd.DataFrame(st.session_state.project_data['initial_data'])
                else:
                    st.session_state.all_training_data = pd.DataFrame()
            
            st.session_state.cycle_data = project_data['cycle_data']
            
            # ML 모델 복원
            if project_data['ml_trainer']:
                st.session_state.ml_trainer = project_data['ml_trainer']
            else:
                st.session_state.ml_trainer = MLModelTrainer(model_preference='linear_focused', encoding_method='auto', target_transform='auto')
            
            # 다른 객체들 초기화
            st.session_state.bayesian_optimizer = None
            st.session_state.mapping_generator = MappingFileGenerator()
            
            st.success(f"프로젝트 '{project_data['config']['project_name']}'을 로드했습니다!")
            st.rerun()
            
        except Exception as e:
            st.error(f"프로젝트 로드 실패: {str(e)}")
    
    def save_current_project(self):
        """현재 프로젝트 저장"""
        if not st.session_state.current_project:
            st.warning("저장할 프로젝트가 선택되지 않았습니다.")
            return
        
        try:
            # 세션 상태 정리 및 저장
            session_data = {
                'current_step': st.session_state.current_step,
                'current_cycle': st.session_state.current_cycle,
                'in_cycle_phase': st.session_state.in_cycle_phase,
                'project_data': st.session_state.project_data,
                'all_training_data': st.session_state.all_training_data,
                'cycle_data': st.session_state.cycle_data,
                'ml_trainer': st.session_state.ml_trainer
            }
            
            st.session_state.data_manager.save_project(st.session_state.current_project, session_data)
            
        except Exception as e:
            st.error(f"프로젝트 저장 실패: {str(e)}")
    
    def find_top_predicted_conditions(self, ml_trainer, n_top=10):
        """전체 파라미터 공간에서 최고 예측값 조건들을 찾기"""
        try:
            if not hasattr(ml_trainer, 'feature_names') or not ml_trainer.feature_names:
                print("❌ ML 모델의 feature_names가 없습니다.")
                return []
            
            # 현재 데이터에서 각 특성의 범위 파악
            df = st.session_state.all_training_data
            
            # 실제 학습에 사용된 특성만 필터링 (식별자 컬럼 제외)
            exclude_patterns = ['Sample_ID', 'sample_id', 'ID', 'id', 'Unnamed:', 'unnamed:', 'Well', 'well', 'Index', 'index']
            valid_features = []
            
            for feature in ml_trainer.feature_names:
                # 제외 패턴 체크
                is_excluded = any(pattern in feature for pattern in exclude_patterns)
                if not is_excluded and feature in df.columns:
                    valid_features.append(feature)
                else:
                    print(f"⚠️ 특성 '{feature}' 제외됨 (식별자 또는 데이터에 없음)")
            
            if not valid_features:
                print("❌ 사용 가능한 특성이 없습니다.")
                return []
            
            print(f"✅ 사용할 특성 ({len(valid_features)}개): {valid_features}")
            
            # 그리드 포인트 생성
            grid_points = []
            categorical_features = {}
            
            for feature in valid_features:
                    
                if df[feature].dtype == 'object':
                    # 범주형 변수
                    unique_values = df[feature].unique().tolist()
                    categorical_features[feature] = unique_values
                else:
                    # 연속 변수: 범위를 10개 구간으로 나누기
                    min_val = df[feature].min()
                    max_val = df[feature].max()
                    if min_val == max_val:
                        grid_points.append([min_val])
                    else:
                        grid_points.append(np.linspace(min_val, max_val, 10))
            
            # 조합 생성 (너무 많으면 샘플링)
            import itertools
            
            # 범주형 변수 처리
            combinations = []
            max_combinations = 1000  # 최대 조합 수 제한
            
            if len(grid_points) > 0:
                # 연속 변수들의 조합 생성
                continuous_combos = list(itertools.product(*grid_points))
                
                # 범주형 변수 조합 추가
                if categorical_features:
                    categorical_combos = list(itertools.product(*categorical_features.values()))
                    
                    # 연속+범주형 조합
                    all_combos = []
                    for cont_combo in continuous_combos[:max_combinations//len(categorical_combos) if categorical_combos else max_combinations]:
                        for cat_combo in categorical_combos:
                            combo = {}
                            # 연속 변수 추가
                            cont_idx = 0
                            for feature in valid_features:  # valid_features 사용
                                if feature in df.columns and df[feature].dtype != 'object':
                                    if cont_idx < len(cont_combo):
                                        combo[feature] = cont_combo[cont_idx]
                                        cont_idx += 1
                            
                            # 범주형 변수 추가
                            cat_idx = 0
                            for feature in valid_features:  # valid_features 사용
                                if feature in categorical_features:
                                    if cat_idx < len(cat_combo):
                                        combo[feature] = cat_combo[cat_idx]
                                        cat_idx += 1
                            
                            all_combos.append(combo)
                else:
                    # 연속 변수만 있는 경우
                    all_combos = []
                    for combo in continuous_combos[:max_combinations]:
                        combo_dict = {}
                        for i, feature in enumerate(valid_features):  # valid_features 사용
                            if feature in df.columns and i < len(combo):
                                combo_dict[feature] = combo[i]
                        all_combos.append(combo_dict)
                
                combinations = all_combos
            
            # 각 조합에 대해 예측 수행
            top_results = []
            
            for combo in combinations[:max_combinations]:
                try:
                    # 예측 수행 - valid_features만 사용
                    combo_df = pd.DataFrame([combo])
                    
                    # 누락된 특성 채우기 (valid_features 기준)
                    for feature in valid_features:
                        if feature not in combo_df.columns:
                            combo_df[feature] = 0
                    
                    # 특성 순서 맞추기 (valid_features 순서로)
                    combo_df = combo_df[valid_features]
                    
                    # 인코딩
                    X_encoded = combo_df.copy()
                    for column in X_encoded.columns:
                        if column in ml_trainer.label_encoders:
                            le = ml_trainer.label_encoders[column]
                            if X_encoded[column].iloc[0] in le.classes_:
                                X_encoded[column] = le.transform(X_encoded[column])
                            else:
                                X_encoded[column] = 0
                    
                    # 스케일링
                    X_scaled = ml_trainer.scaler.transform(X_encoded)
                    
                    # 예측
                    prediction = ml_trainer.best_model.predict(X_scaled)[0]
                    
                    # 결과 저장
                    result = combo.copy()
                    result['predicted_yield'] = round(prediction, 3)
                    top_results.append(result)
                    
                except Exception as e:
                    continue
            
            # 상위 결과 반환
            top_results.sort(key=lambda x: x['predicted_yield'], reverse=True)
            return top_results[:n_top]
            
        except Exception as e:
            print(f"최고 예측 조건 탐색 중 오류: {str(e)}")
            return []
    
    def auto_save(self):
        """자동 저장 (오류 발생 시 무시)"""
        if st.session_state.current_project:
            try:
                session_data = {
                    'current_step': st.session_state.current_step,
                    'current_cycle': st.session_state.current_cycle,
                    'in_cycle_phase': st.session_state.in_cycle_phase,
                    'project_data': st.session_state.project_data,
                    'all_training_data': st.session_state.all_training_data,
                    'cycle_data': st.session_state.cycle_data,
                    'ml_trainer': st.session_state.ml_trainer
                }
                st.session_state.data_manager.save_project(st.session_state.current_project, session_data)
            except:
                pass  # 자동 저장 실패는 무시
    
    def reset_session_for_new_project(self):
        """새 프로젝트를 위한 세션 초기화"""
        st.session_state.current_step = 0
        st.session_state.current_cycle = 0
        st.session_state.in_cycle_phase = False
        st.session_state.project_data = {}
        st.session_state.ml_trainer = MLModelTrainer(model_preference='linear_focused', encoding_method='auto', target_transform='auto')
        st.session_state.bayesian_optimizer = None
        st.session_state.mapping_generator = MappingFileGenerator()
        st.session_state.cycle_data = []
        st.session_state.all_training_data = pd.DataFrame()


def main():
    st.set_page_config(
        page_title="ML Protogen System",
        page_icon="🧬",
        layout="wide"
    )
    
    # 프로젝트 매니저 초기화
    project_manager = ProjectManager()
    project_manager.init_session_state()
    
    # 통합 사이드바 생성
    project_manager.create_unified_sidebar()
    
    # 메인 컨텐츠
    if st.session_state.current_project:
        # 프로젝트가 선택된 경우 진행 단계 실행
        
        # 자동 저장 버튼
        col_save1, col_save2, col_save3 = st.columns([1, 1, 3])
        with col_save1:
            if st.button("💾 저장", help="현재 진행상황 저장"):
                project_manager.save_current_project()
                st.success("저장 완료!")
        
        with col_save2:
            # 프로젝트 정보 표시
            project_info = st.session_state.data_manager.get_project_info(st.session_state.current_project)
            if project_info:
                st.info(f"**{project_info.get('project_name', 'Unknown')}** (단계 {st.session_state.current_step + 1})")
        
        st.markdown("---")
        
        # 프로젝트 구조 표시 (요청된 경우)
        if st.session_state.get('show_project_structure', False):
            project_manager.show_project_structure()
            st.session_state.show_project_structure = False  # 한 번 표시 후 리셋
        
        # 현재 단계 실행
        project_manager.run_step()
        
    else:
            # 프로젝트가 선택되지 않은 경우
            st.title("🧬 ML Protogen System")
            st.markdown("---")
            
            st.header("환영합니다!")
            st.markdown("""
            ### 시작하기
            
            왼쪽 패널에서 다음 중 하나를 선택하세요:
            
            1. **📊 기존 프로젝트 선택**: 이미 생성된 프로젝트를 클릭하여 계속 진행
            2. **➕ 새 프로젝트 생성**: "새 프로젝트 만들기"를 확장하여 새로운 실험 프로젝트 시작
            
            ### 시스템 특징
            
            - **반복적 학습**: 초기 데이터 → 모델 학습 → 모델 분석 → 베이지안 최적화 실험 설계 → 실험 → 결과 입력 → 모델 개선 사이클
            - **프로젝트 관리**: 여러 프로젝트를 동시에 관리하고 언제든지 이전 상태로 복원
            - **자동 저장**: 프로젝트 진행 상황이 자동으로 파일에 저장
            - **데이터 시각화**: 각 단계별 결과를 그래프와 차트로 확인
            
            ### 지원하는 실험 유형
            
            - 🧬 **Protein Expression**: 프로테인 발현 최적화
            - ⚗️ **Metabolic Engineering**: 대사 공학 실험
            - 🧪 **Gene Regulation**: 유전자 발현 조절
            - 🔬 **Custom**: 사용자 정의 실험
            """)
            
            # 샘플 프로젝트 생성 버튼
            if st.button("🚀 샘플 프로젝트로 시작하기", help="데모 데이터로 빠르게 시작"):
                try:
                    # 샘플 프로젝트 생성
                    from datetime import datetime
                    sample_name = f"Sample_Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    safe_name = st.session_state.data_manager.create_project(sample_name)
                    
                    # 프로젝트 목록 새로고침
                    st.session_state.project_list = st.session_state.data_manager.get_project_list()
                    
                    # 샘플 프로젝트로 전환
                    project_manager.load_project(safe_name)
                    
                    # 샘플 데이터 추가
                    st.session_state.project_data.update({
                        'project_name': sample_name,
                        'project_description': '샘플 프로젝트 - 프로테인 발현 최적화 데모',
                        'experiment_type': 'Protein Expression',
                        'optimization_target': 'Maximize',
                        'target_metric': 'Expression_Level',
                        'expected_samples': 50
                    })
                    
                    st.success("샘플 프로젝트가 생성되었습니다!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"샘플 프로젝트 생성 실패: {str(e)}")
    
    # 페이지 하단에 앱 종료 시 자동 저장 구현
    if st.session_state.current_project:
        # 페이지 새로고침이나 종료 시 자동 저장되도록 주기적으로 저장
        import time
        current_time = time.time()
        if 'last_save_time' not in st.session_state:
            st.session_state.last_save_time = current_time
        
        # 5분마다 자동 저장
        if current_time - st.session_state.last_save_time > 300:  # 300초 = 5분
            project_manager.save_current_project()
            st.session_state.last_save_time = current_time


if __name__ == "__main__":
    main()