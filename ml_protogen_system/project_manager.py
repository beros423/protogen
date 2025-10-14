import os
import json
import pandas as pd
import joblib
from datetime import datetime
from typing import Dict, List, Any, Optional
import streamlit as st


class ProjectDataManager:
    def __init__(self, base_path: str = "projects"):
        self.base_path = base_path
        self.ensure_base_directory()
    
    def ensure_base_directory(self):
        """기본 프로젝트 디렉토리 생성"""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
    
    def get_project_list(self) -> List[str]:
        """프로젝트 목록 반환"""
        if not os.path.exists(self.base_path):
            return []
        
        projects = []
        for item in os.listdir(self.base_path):
            project_path = os.path.join(self.base_path, item)
            if os.path.isdir(project_path):
                config_path = os.path.join(project_path, "project_config.json")
                if os.path.exists(config_path):
                    projects.append(item)
        return sorted(projects)
    
    def create_project(self, project_name: str) -> str:
        """새 프로젝트 생성"""
        # 프로젝트 이름 정리 (파일시스템 안전)
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        project_path = os.path.join(self.base_path, safe_name)
        
        if os.path.exists(project_path):
            raise ValueError(f"프로젝트 '{safe_name}'이 이미 존재합니다.")
        
        # 프로젝트 디렉토리 구조 생성
        os.makedirs(project_path)
        os.makedirs(os.path.join(project_path, "data"))
        os.makedirs(os.path.join(project_path, "models"))
        os.makedirs(os.path.join(project_path, "results"))
        os.makedirs(os.path.join(project_path, "cycles"))
        
        # 초기 프로젝트 설정 저장
        initial_config = {
            "project_name": project_name,
            "safe_name": safe_name,
            "created_at": datetime.now().isoformat(),
            "current_step": 0,
            "current_cycle": 0,
            "in_cycle_phase": False
        }
        
        config_path = os.path.join(project_path, "project_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(initial_config, f, indent=2, ensure_ascii=False)
        
        return safe_name
    
    def load_project(self, project_safe_name: str) -> Dict[str, Any]:
        """프로젝트 데이터 로드"""
        project_path = os.path.join(self.base_path, project_safe_name)
        
        if not os.path.exists(project_path):
            raise ValueError(f"프로젝트 '{project_safe_name}'을 찾을 수 없습니다.")
        
        # 프로젝트 설정 로드
        config_path = os.path.join(project_path, "project_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 프로젝트 데이터 로드
        data_path = os.path.join(project_path, "project_data.json")
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
        else:
            project_data = {}
        
        # 누적 학습 데이터 로드
        training_data_path = os.path.join(project_path, "data", "all_training_data.csv")
        if os.path.exists(training_data_path):
            all_training_data = pd.read_csv(training_data_path)
        else:
            all_training_data = pd.DataFrame()
        
        # 사이클 데이터 로드
        cycle_data = []
        cycles_path = os.path.join(project_path, "cycles")
        if os.path.exists(cycles_path):
            for cycle_file in sorted(os.listdir(cycles_path)):
                if cycle_file.endswith('.json'):
                    cycle_path = os.path.join(cycles_path, cycle_file)
                    with open(cycle_path, 'r', encoding='utf-8') as f:
                        cycle_data.append(json.load(f))
        
        # ML 모델 로드
        model_path = os.path.join(project_path, "models", "ml_trainer.joblib")
        ml_trainer = None
        if os.path.exists(model_path):
            try:
                from ml_core import MLModelTrainer
                ml_trainer = MLModelTrainer()
                ml_trainer.load_model(model_path)
            except:
                ml_trainer = None
        
        return {
            "config": config,
            "project_data": project_data,
            "all_training_data": all_training_data,
            "cycle_data": cycle_data,
            "ml_trainer": ml_trainer,
            "project_path": project_path
        }
    
    def save_project(self, project_safe_name: str, session_state: Dict[str, Any]):
        """프로젝트 데이터 저장"""
        project_path = os.path.join(self.base_path, project_safe_name)
        
        if not os.path.exists(project_path):
            raise ValueError(f"프로젝트 '{project_safe_name}'을 찾을 수 없습니다.")
        
        # 프로젝트 설정 업데이트
        config_path = os.path.join(project_path, "project_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config.update({
            "current_step": session_state.get('current_step', 0),
            "current_cycle": session_state.get('current_cycle', 0),
            "in_cycle_phase": session_state.get('in_cycle_phase', False),
            "last_updated": datetime.now().isoformat()
        })
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 프로젝트 데이터 저장
        project_data = session_state.get('project_data', {})
        # DataFrame 객체를 딕셔너리로 변환
        serializable_data = {}
        for key, value in project_data.items():
            if isinstance(value, pd.DataFrame):
                serializable_data[key] = {
                    'type': 'dataframe',
                    'data': value.to_dict('records'),
                    'columns': list(value.columns)
                }
            else:
                serializable_data[key] = value
        
        data_path = os.path.join(project_path, "project_data.json")
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False, default=str)
        
        # 누적 학습 데이터 저장
        all_training_data = session_state.get('all_training_data', pd.DataFrame())
        if not all_training_data.empty:
            training_data_path = os.path.join(project_path, "data", "all_training_data.csv")
            all_training_data.to_csv(training_data_path, index=False)
        
        # 사이클 데이터 저장
        cycle_data = session_state.get('cycle_data', [])
        cycles_path = os.path.join(project_path, "cycles")
        for i, cycle in enumerate(cycle_data):
            cycle_file_path = os.path.join(cycles_path, f"cycle_{i+1}.json")
            with open(cycle_file_path, 'w', encoding='utf-8') as f:
                json.dump(cycle, f, indent=2, ensure_ascii=False, default=str)
        
        # ML 모델 저장
        ml_trainer = session_state.get('ml_trainer')
        if ml_trainer and hasattr(ml_trainer, 'best_model') and ml_trainer.best_model is not None:
            model_path = os.path.join(project_path, "models", "ml_trainer.joblib")
            ml_trainer.save_model(model_path)
    
    def delete_project(self, project_safe_name: str):
        """프로젝트 삭제"""
        project_path = os.path.join(self.base_path, project_safe_name)
        
        if not os.path.exists(project_path):
            raise ValueError(f"프로젝트 '{project_safe_name}'을 찾을 수 없습니다.")
        
        import shutil
        shutil.rmtree(project_path)
    
    def get_project_info(self, project_safe_name: str) -> Dict[str, Any]:
        """프로젝트 정보 조회"""
        project_path = os.path.join(self.base_path, project_safe_name)
        
        if not os.path.exists(project_path):
            return {}
        
        config_path = os.path.join(project_path, "project_config.json")
        if not os.path.exists(config_path):
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 추가 정보 계산
        data_path = os.path.join(project_path, "data", "all_training_data.csv")
        data_count = 0
        if os.path.exists(data_path):
            try:
                df = pd.read_csv(data_path)
                data_count = len(df)
            except:
                pass
        
        cycles_path = os.path.join(project_path, "cycles")
        cycle_count = 0
        if os.path.exists(cycles_path):
            cycle_count = len([f for f in os.listdir(cycles_path) if f.endswith('.json')])
        
        config['data_count'] = data_count
        config['cycle_count'] = cycle_count
        
        return config
    
    def export_project(self, project_safe_name: str) -> str:
        """프로젝트 전체 데이터 내보내기"""
        project_path = os.path.join(self.base_path, project_safe_name)
        
        if not os.path.exists(project_path):
            raise ValueError(f"프로젝트 '{project_safe_name}'을 찾을 수 없습니다.")
        
        # ZIP 파일로 압축
        import zipfile
        export_path = f"{project_safe_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, project_path)
                    zipf.write(file_path, arcname)
        
        return export_path