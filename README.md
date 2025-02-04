# protogen
liquid handler protocol generator

## updates

####  2024-10-08 최초 버전
- Stocking plate 포맷 기준 설정
- Plate가 sheet 단위로 구분될 것
- 첫 번째 [A] cell 기준으로 정렬될 것
- 기본 사용법 정리
    - OT2-7.py 실행 방법 안내 (streamlit run OT2-7.py)
    - 필요 라이브러리 설치 방법 (pip install streamlit, pip install pandas)
- Destination plate 관련 제한사항 안내
    - 현재 assembly 개수 증가 시 row는 A 고정, column만 증가
- 기본적인 OT2 프로토콜 적용


####  2024-10-21 업데이트
- 파트 자동인식 규칙 설정
    - Promoter: P
    - CDS: C
    - Connector: N
    - Terminator: T
    - Connector 시작부품: S, 끝부품: E
- Connector 자동설정
- Row 추가 시 자동으로 적절한 옵션 선택
- Connector가 없을 경우 마지막 part 반복
- End part list 분리 → 마지막 Connector 자동 설정 기능 추가 예정
- Protocol 버그 수정  
- Protocol 파일 자동 생성 기능 추가
    - OT2-7.py가 있는 폴더에 OT2_protocol.py 파일 생성
  
> OT-2 simulate 테스트 완료

####  2024-10-21 (추가 업데이트)
- 자동인식 규칙 수정
    - (P), (T), (N), (C) → Stocking plate 참고
- Connector 자동설정 및 선택 비활성화
- Editable Table 추가 (sample 수정 가능, volume & concentration 임시값 설정)
- Common Parts 추가 가능
    - ex) GGA mixture
- Source plate에서 categorize되지 않은 파트도 인식
- 각 파트별 volume 설정 추가
- 일부 기능 수정 (fx 수정)
- Source volume 부족 시 다음 well로 이동하는 기능 추가(그래도 부족하면 에러 표시)
- Protocol에 간단한 주석 추가 (어떤 작업이 수행되는지 명시)

추가 논의 필요:
Source plate 데이터 입력 방식 개선 필요 (현재 동일 volume 가정)
농도 기준 계산 방식 도입 고려 가능 (Assembly Design에서 concentration 지정)
UI 개선 필요 (정리 방안 아이디어 요청)

#### 2024-11-12 업데이트
- Plate 읽을 때 volume 일괄설정 기능 추가 (임시)
- 파트 선택 방식을 조합형으로 변경
    - 여러 파트를 선택할 수 있으며, 결과물의 경우 해당 파트들로 가능한 모든 조합을 출력

####  2024-11-
