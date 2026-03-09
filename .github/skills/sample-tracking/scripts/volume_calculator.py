#!/usr/bin/env python3
"""
샘플 용량 계산 유틸리티

다양한 단위 변환 및 계산 기능 제공
"""

import re
from typing import Optional, Tuple


class VolumeUnit:
    """용량 단위 변환"""
    
    # 기준: μL (마이크로리터)
    UNITS = {
        'μL': 1,
        'ul': 1,
        'μl': 1,
        'uL': 1,
        'mL': 1000,
        'ml': 1000,
        'L': 1_000_000,
        'l': 1_000_000,
    }
    
    @classmethod
    def parse(cls, volume_str: str) -> Optional[Tuple[float, str]]:
        """
        용량 문자열 파싱
        
        Args:
            volume_str: "50 μL", "2.5 mL", "1 L" 등
        
        Returns:
            (value, unit) 또는 None
        """
        if not volume_str:
            return None
        
        # 패턴: 숫자 + 공백(선택) + 단위
        pattern = r'(\d+(?:\.\d+)?)\s*(μL|ul|μl|uL|mL|ml|L|l)'
        match = re.search(pattern, volume_str)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            return (value, unit)
        
        return None
    
    @classmethod
    def to_microliters(cls, value: float, unit: str) -> float:
        """
        모든 단위를 μL로 변환
        
        Examples:
            to_microliters(2.5, 'mL') -> 2500.0
            to_microliters(50, 'μL') -> 50.0
        """
        multiplier = cls.UNITS.get(unit, 1)
        return value * multiplier
    
    @classmethod
    def from_microliters(cls, microliters: float, target_unit: str) -> float:
        """
        μL을 다른 단위로 변환
        
        Examples:
            from_microliters(2500, 'mL') -> 2.5
        """
        multiplier = cls.UNITS.get(target_unit, 1)
        return microliters / multiplier
    
    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> float:
        """
        단위 간 변환
        
        Examples:
            convert(2.5, 'mL', 'μL') -> 2500.0
        """
        microliters = cls.to_microliters(value, from_unit)
        return cls.from_microliters(microliters, to_unit)
    
    @classmethod
    def format(cls, microliters: float, prefer_unit: str = 'auto') -> str:
        """
        μL을 읽기 좋은 형태로 포맷
        
        Args:
            microliters: μL 단위 값
            prefer_unit: 'auto', 'μL', 'mL', 'L'
        
        Returns:
            "50 μL", "2.5 mL" 등
        """
        if prefer_unit == 'auto':
            # 자동 단위 선택
            if microliters >= 1_000_000:
                return f"{microliters / 1_000_000:.1f} L"
            elif microliters >= 1000:
                return f"{microliters / 1000:.1f} mL"
            else:
                return f"{microliters:.1f} μL"
        else:
            value = cls.from_microliters(microliters, prefer_unit)
            return f"{value:.1f} {prefer_unit}"


class MassUnit:
    """질량 단위 변환 (농도 계산용)"""
    
    # 기준: ng (나노그램)
    UNITS = {
        'ng': 1,
        'μg': 1000,
        'ug': 1000,
        'mg': 1_000_000,
        'g': 1_000_000_000,
    }
    
    @classmethod
    def parse(cls, mass_str: str) -> Optional[Tuple[float, str]]:
        """질량 문자열 파싱"""
        if not mass_str:
            return None
        
        pattern = r'(\d+(?:\.\d+)?)\s*(ng|μg|ug|mg|g)'
        match = re.search(pattern, mass_str)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            return (value, unit)
        
        return None
    
    @classmethod
    def to_nanograms(cls, value: float, unit: str) -> float:
        """모든 단위를 ng로 변환"""
        multiplier = cls.UNITS.get(unit, 1)
        return value * multiplier


class ConcentrationCalculator:
    """농도 계산"""
    
    @staticmethod
    def calculate_total_mass(volume_str: str, concentration_str: str) -> Optional[str]:
        """
        총 질량 계산
        
        Args:
            volume_str: "50 μL"
            concentration_str: "100 ng/μL"
        
        Returns:
            "5000 ng" 또는 None
        """
        vol = VolumeUnit.parse(volume_str)
        if not vol:
            return None
        
        # 농도 파싱 (예: "100 ng/μL")
        conc_match = re.search(r'(\d+(?:\.\d+)?)\s*(ng|μg|mg)/μL', concentration_str)
        if not conc_match:
            return None
        
        conc_value = float(conc_match.group(1))
        conc_unit = conc_match.group(2)
        
        # μL로 변환
        volume_ul = VolumeUnit.to_microliters(vol[0], vol[1])
        
        # 총 질량 계산
        total_ng = MassUnit.to_nanograms(conc_value * volume_ul, conc_unit)
        
        # 읽기 좋은 형태로 변환
        if total_ng >= 1_000_000:
            return f"{total_ng / 1_000_000:.1f} mg"
        elif total_ng >= 1000:
            return f"{total_ng / 1000:.1f} μg"
        else:
            return f"{total_ng:.1f} ng"
    
    @staticmethod
    def calculate_dilution(initial_conc: str, target_conc: str, 
                          final_volume_str: str) -> Optional[Dict[str, str]]:
        """
        희석 계산 (C1V1 = C2V2)
        
        Returns:
            {
                "sample_volume": "10 μL",
                "diluent_volume": "40 μL",
                "final_volume": "50 μL"
            }
        """
        # 농도 파싱
        c1_match = re.search(r'(\d+(?:\.\d+)?)\s*ng/μL', initial_conc)
        c2_match = re.search(r'(\d+(?:\.\d+)?)\s*ng/μL', target_conc)
        
        if not c1_match or not c2_match:
            return None
        
        c1 = float(c1_match.group(1))
        c2 = float(c2_match.group(1))
        
        # 최종 용량 파싱
        v2_parsed = VolumeUnit.parse(final_volume_str)
        if not v2_parsed:
            return None
        
        v2 = VolumeUnit.to_microliters(v2_parsed[0], v2_parsed[1])
        
        # C1V1 = C2V2 -> V1 = C2V2/C1
        v1 = (c2 * v2) / c1
        diluent = v2 - v1
        
        return {
            'sample_volume': VolumeUnit.format(v1),
            'diluent_volume': VolumeUnit.format(diluent),
            'final_volume': VolumeUnit.format(v2)
        }


# 사용 예시
if __name__ == '__main__':
    # 용량 변환
    print("=== 용량 변환 ===")
    print(VolumeUnit.convert(2.5, 'mL', 'μL'))  # 2500.0
    print(VolumeUnit.format(2500))  # "2.5 mL"
    print(VolumeUnit.format(50))  # "50.0 μL"
    
    # 총 질량 계산
    print("\n=== 총 질량 계산 ===")
    total = ConcentrationCalculator.calculate_total_mass("50 μL", "100 ng/μL")
    print(f"Total mass: {total}")  # "5.0 μg"
    
    # 희석 계산
    print("\n=== 희석 계산 ===")
    dilution = ConcentrationCalculator.calculate_dilution(
        "100 ng/μL", "20 ng/μL", "50 μL"
    )
    print(f"Sample: {dilution['sample_volume']}")  # "10.0 μL"
    print(f"Diluent: {dilution['diluent_volume']}")  # "40.0 μL"
