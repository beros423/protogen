## protogen 설명서

이 문서는 `protogen.py`의 실행법, 필요한 패키지, 프로그램 개요 및 사용법(입력 포맷 설명 포함)을 자세히 정리한 설명서입니다.

## 1. 실행법 및 필요 패키지

#### Requirements
- Python 3.8+ 권장
- `requirements.txt`에 정의된 패키지 (이 프로젝트 루트에 `requirements.txt`가 있습니다).

#### Installation (Windows PowerShell)
```powershell
# 가상환경 생성
python -m venv .venv; .\.venv\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt
```

#### 앱 실행
Streamlit 앱으로 실행합니다:
```powershell
streamlit run protogen.py
```

앱 실행 후 브라우저에서 Streamlit이 열리며, 화면 왼쪽의 사이드바에서 단계(Inputs → Design → Set Commons → Results)를 따라 진행합니다.

## 2. 프로그램 개요 (용도 및 기능)

`protogen.py`는 EffiModular를 이용한 합성생물학 조립(assembly) 설계를 돕는 Streamlit 기반의 GUI 도구입니다. 
기본 기능은 다음과 같습니다:

- 출처(소스) 파트(프롬포터, CDS, 터미네이터, 커넥터 등)를 불러와 재고(plate, well, volume)를 관리
- 사용자가 그룹(assembly group)과 각 그룹 내 조립 대상(TU, transcriptional unit)을 정의
- 각 TU 및 실험 조건에 대한 상세한 디자인 선택을 지원
- Lv1 (TU 단위) 및 Lv2 (조합 결과) 출력 설계를 자동으로 생성
- 각 파트의 소요량, 웰 분배 계산(최대 Well 볼륨, dead volume 반영)
- OT-2 로봇용 Python 프로토콜(스크립트)로 변환(옵션)

## 3. 사용법

아래는 각 단계별 입력 항목과 파일 포맷에 대한 상세 설명입니다.

#### STEP 1. Input Sources (소스 입력)

앱 시작 시 첫 단계입니다. 소스(Stock) 파일을 불러와야 합니다.

- 지원 포맷
  - sources는 CSV 또는 Excel(xlsx) 포맷을 지원합니다.  

- CSV 소스 파일(권장) 컬럼 구조
  - 필수 컬럼: type, name, plate, well, volume, note
  - 각 행은 하나의 소스(파트)를 의미합니다.
    - type: 파트의 종류(예: Promoter, CDS, Terminator, Connector)
    - name: 파트 이름(예: (P)TDH, (C)Venus, (T)ENO1, (N)s|1 등)
    - plate: 소스가 있는 plate 이름 (앱에서 공백은 '_'로 대체될 수 있음)
    - well: 웰 코드 (예: A1)
    - volume: 해당 웰에 남아있는 볼륨(ul)
    - note: 선택적 메모

  - 예시 CSV(헤더 포함)

    |type|name|plate|well|volume|note|
    |----|----|----|----|----|----|
    |Promoter|(P)TDH|Stock_plate1|A1|10000|-|
    |CDS|(C)Venus|Stock_plate1|A2|10000|-|
    |Terminator|(T)ENO1|Stock_plate1|A3|10000|-|
    |Connector|(N)s\|1|Stock_plate1|A4|10000|-|

- Legacy Input
  - 각 파트의 type/plate/volume 정보 없이 Wellplate의 위치정보만으로 입력하는 형식입니다. 보다 직관적인 입력을 위한 기능입니다. 
  - 구현상 시트별로 특정 형식(앱 코드 내에서 'A' 값을 시작점으로 찾는 로직 등)을 요구합니다. 샘플 엑셀(예: `plate_sample.xlsx`)을 참고하여 작성하는 것을 권장합니다.
  - Excel 로딩은 시트 이름을 읽어 plate 이름으로 사용합니다.
  - 파트의 type은 각 파트 이름의 접두사로부터 유추됩니다. (예: (P) → Promoter, (C) → CDS, (T) → Terminator, (N) → Connector)

    |-|1|2|3|...|
    |---|---|---|---|---|
    |A|(P)1	|(T)1	|(N)s\|1	||
    |B|(P)2	|(P)2	|(N)1\|2	||
    |C|(C)1	|(C)2	|(N)2\|e	||
    |...|||||



- 입력 검증
  - source에는 반드시 'Promoter', 'CDS', 'Terminator', 'Connector' 타입이 존재해야 합니다.

#### STEP 2. Design (디자인)

Design 단계에서는 각 TU에 들어갈 파트 조합과 볼륨을 설정합니다.

- Volume setting
  - TU 당 기본 볼륨(예: Promoter 2 ul, CDS 2 ul, Terminator 2 ul, Connector 2 ul)을 설정합니다.
  - 'Maximum volume of single well' (예: 50 ul) 및 Lv2 dead volume(권장 2 ul)을 고려하여 웰 분배를 계산합니다.
  - Dead volume은 각 웰에서 남겨두는 최소 볼륨으로, 웰 간 이동 시 손실을 방지하기 위해 사용됩니다.

- Groups
  - 그룹 수와 각 그룹의 이름, 각 그룹당 TU 수(Number of TU)를 지정합니다.
  - 외부 파일(CSV/JSON)에서 디자인을 불러올 수 있습니다. 예시 포맷을 참고하세요.
    - CSV 포맷: `Group,Promoter,CDS,Terminator` 형태의 CSV를 사용합니다. 각 셀에 세미콜론(;)로 여러 선택지를 넣을 수 있습니다.
    
        |Group      |Promoter|CDS|Terminator|
        |--|--|--|--|
        |Group_1	|(P)TDH	|(C)mTurquiose2	|(T)ENO1|
        |Group_1	|(P)RPL18B	|(C)Venus	|(T)ISSA1|
        |Group_1	|(P)RAD27	|(C)mRuby2	|(T)ADH1|
        |Group_2	|(P)CCW12	|(C)Cas9	|(T)PGK1|
        |Group_2	|(P)ALD6	|(C)I-Scei (ORF)	|(T)ENO2|

    - JSON 포맷: group name, number_of_tu, designs(각 TU의 파트 조합 리스트) 형태의 JSON 배열을 사용합니다.
        ```json
        [
          {
            "group_name":"Group_1",
            "number_of_tu":3,
            "designs":[{"Promoter":["(P)TDH"],"CDS":["(C)Venus"],"Terminator":["(T)ENO1"]},...]
          }
        ]
        ```

- TU design (Detailed TU Design Selection)
  - 각 그룹 내에서 Promoter/CDS/Terminator/Connector를 다중 선택(multiselect)으로 지정할 수 있습니다. 다중 선택된 항목들의 모든 조합이 생성됩니다.
  - Connector는 단일 선택 로직(자동 인덱스 지정 및 일부 행에서 비활성화)로 처리됩니다. Circuit 내부에서 연결되는 순서대로 각 TU를 입력하세요. 
  - 사용자가 입력한 조합(다중 선택의 각 조합)을 바탕으로 가능한 TU 목록이 만들어집니다.

  
  


#### STEP 3. Set Commons (공통 부품 설정)

이 단계에서는 각 Lv1 TU에 항상 포함되는 공통 부품(Lv1 commons)과 Lv2 조합에 항상 포함되는 공통 부품(Lv2 commons)을 지정합니다.

- 입력 항목
  - Part name: 공통 부품 이름
  - Volume (ul): 각 TU 당 사용할 볼륨
  - Stock plate: 소스에 없는 경우 새로 지정할 plate
  - Stock location (well): 소스에 없는 경우 지정할 well

- 동작
  - 만약 입력한 이름이 이미 sources(입력된 소스 데이터)에 존재하면, 해당 소스의 plate/well/volume을 사용합니다. 

#### STEP 4. Results (결과)

Results 단계는 실제 출력 매핑(웰 배치)과 OT-2 변환(옵션)을 생성합니다.
  - Destination Plate type 및 name을 지정할 수 있습니다.
  - Lv1 및 Lv2 매핑을 각각 생성하며, Lv2 매핑은 Lv1 Output을 바탕으로 생성됩니다.

  
- 계산
  - 각 디자인 항목에 대해 필요 총 볼륨(need_vol) = tu_usage * total_vol
  - 웰 수 계산(wells_required) = need_vol / (lv1_maxvol - lv2_deadvol) (반올림 처리)
  - 웰 당 볼륨(volume_for_each_well) = need_vol / wells_required + lv2_deadvol
  - 총 볼륨(total_vol) = wells_required * volume_for_each_well

- 출력
  - Lv1 mapping: 각 TU를 대상으로 생성된 aspiration/dispense 작업 목록(Protocol)을 생성합니다.
  - Lv1_output_plates: Lv1 조합 결과 각 TU가 어떤 plate/well에 위치하는지 표시합니다. 이 정보는 Lv2 매핑에 그대로 이용되므로, 사용자가 숙지할 필요는 없습니다. 
  - Lv2 outputs: Lv1 결과를 조합하여 Lv2 조립을 위한 작업 목록을 생성합니다.
  - updated sources: 각 소스의 남은 볼륨을 반영한 업데이트된 소스 목록을 제공합니다.

- mapping 변환
  - 위 aspiration/dispense 작업 목록을 지원하지 않는 Liquid Handler를 위해 포맷을 변환합니다. 현재 OT-2 변환만 지원합니다.
  - OT-2 변환
    - OT-2용 Python 스크립트(Protocol API)를 생성합니다.
    - 사용자가 labware 타입과 위치를 직접 지정할 수 있습니다.

## 4. 빠른 사용

1) 가상환경 생성 및 의존성 설치
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2) 앱 실행
```powershell
streamlit run protogen.py
```
3) 브라우저에서 앱에 접속

4) Step 1에서 Sourceplate 업로드(또는 기본값 사용)
![alt text](imgs\image-10.png)

5) Design에서 그룹/디자인 설정
![alt text](imgs\image-11.png)
6) Set Commons에서 공통부품 입력
![alt text](imgs\image-12.png)
7) Results에서 결과 확인 및 OT-2 스크립트 변환
