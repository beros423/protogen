# Protogen

Protogen is a Streamlit application for automating liquid handling protocols for Opentrons OT-2 and Janus robotic systems.  
It generates protocols for DNA assembly and helps users intuitively define components, volumes, and well positions.

## Features

- **Excel-based source plate loading**
- **Effimodular experimental design**
- **Automatic OT-2 and Janus protocol/mapping generation**
- **Feedback on required volume and plate usage**

## Installation

Protogen is developed using Python 3.9.

```sh
pip install streamlit pandas opentrons openpyxl
```

## Usage

Run the following command:
```sh
streamlit run protogen.py
```

### 1. File Upload (Input File Format)

Protogen uses Excel files (`.xlsx`) as input.  
Each sheet should contain a table formatted for a 96-well plate, where each cell represents the name of the component at that location.

|    | 1  | 2  | 3  | ...  | 12|
|----|----|----|----|----|----|
| A  | (P)1 | (C)1 | (T)1 |    |
| B  | (P)2 | (C)2 | (T)2 |    |
| C  | (P)3 | (C)3 | (T)3 |    |
| ...|||||
| H  |(P)8|(C)8|(T)8|||  

- Each well (A1, B1, C1, etc.) should contain the names of TU parts (Promoter, CDS, Terminator, etc.).
- Leave empty wells blank.
- Each part is categorized by a header (P, C, T, N) to automatically recognize their positions.
- Identical names are considered as the same part.

|Header|Part|
|----|---------|
|(P)| Promoter |
|(C)| CDS |
|(T)| Terminator |
|(N)| Connector |

### 2. Plate and Volume Configuration

![alt text](image.png)

- Assign names to each plate from the uploaded file.
- Set the default volume for wells without specific volume data.

### 3. Lv1 Design

#### Groups

![alt text](image-2.png)

This feature is for designing multiple plasmids. Each group is designed independently.

- **Number of groups**: Sets the number of groups to divide Transcription Units (TU).
- **Group names**: Assigns names to each group (duplicates may cause errors).
- **Number of TU**: Determines how many TUs each group contains.

#### TU Design

![alt text](image-3.png)

- Define specific TUs per group.
- Each TU contains one CDS, and when multiple promoters and terminators are assigned, all possible combinations are calculated for Lv2 design.
- Combinations with duplicate parts are excluded.
- Connectors remain fixed.

##### Calculation Method  
Each TU includes one CDS, and if multiple Promoters or Terminators are assigned, all possible combinations are generated for Lv2 design.  

For example, a design setup may result in 1+2\*2+3\*2 = 11 TUs. In Lv2, 1\*4\*6 = 24 circuits would be designed, but due to duplicate (T)ENO2, only 15 unique combinations are generated.

<small><small>

||Promoter|CDS|Terminator|Connector|
|:---:|:---------:|:---------:|:----------:|:---------:|
|1|(P)TDH	|(C)mTurquiose2	|(T)ENO1	|(N)s\|1|
|2|(P)RPL18B	|(C)mRuby2	|(T)PGK1	|(N)1\|2|
|3|(P)RPL18B	|(C)mRuby2	|(T)ENO2	|(N)1\|2|
|4|(P)CCW12	|(C)mRuby2	|(T)PGK1	|(N)1\|2|
|5|(P)CCW12	|(C)mRuby2	|(T)ENO2	|(N)1\|2|
|6|(P)CCW12	|(C)Venus	|(T)ENO2	|(N)2\|e|
|7|(P)CCW12	|(C)Venus	|(T)TDH1	|(N)2\|e|
|8|(P)PGK1	|(C)Venus	|(T)ENO2	|(N)2\|e|
|9|(P)PGK1	|(C)Venus	|(T)TDH1	|(N)2\|e|
|10|(P)REV1	|(C)Venus	|(T)ENO2	|(N)2\|e|
|11|(P)REV1	|(C)Venus	|(T)TDH1	|(N)2\|e|

</small></small>

- Searches the uploaded plate for required components and generates assembly combinations.
- Calculates component usage to determine the minimum number of production cycles.
- If the volume exceeds 50 µL, TUs are arranged in repeated 50 µL units.

### 4. Lv2 Assembly Design

#### Input Settings
- **Lv2 Volume Configuration**: Set the volume per TU and dead volume.
- **Lv2 Common Reagents Addition**: Add common reagents such as vectors.

### 5. Protocol Generation and Output Files

- **Select OT-2 or Janus**: Choose the robotic system to execute the protocol.
- **Automatic Protocol Generation**: Generate OT-2 or Janus protocol based on selected settings.
- **Verify Output**: Review final well positions and reagent usage.

## Output Files

- **OT-2 Protocol**: Python script formatted for execution on Opentrons.
- **Janus Protocol**: CSV mapping file for Hamilton Janus.
- **Updated Inventory Information**: Dataframe including updated volume calculations.

## Example Usage

1. Upload the `plate_sample.xlsx` file.
2. Configure well positions and default volume values.
3. Define TU and group settings.
4. Verify volume calculations.
5. Select OT-2 or Janus and generate the protocol.
6. Save the generated protocol and execute it on the robotic system.

## Troubleshooting

- If the program warns about insufficient volume, check and update the inventory volume in the Excel file.
