# Protogen

Protogen is a Streamlit-based application for automating liquid handling protocols for Opentrons OT-2 and Janus robotic systems. It facilitates the creation of protocols for assembling DNA constructs, allowing users to define components, volumes, and well locations.

## Features

- **Automated OT-2 & Janus protocol generation**
- **Excel-based component import**
- **Customizable labware and liquid handling settings**
- **Real-time feedback on required volumes**
- **Group-based assembly management**

## Installation

Ensure you have Python installed (recommended: Python 3.8 or higher), then install dependencies:

```sh
pip install streamlit pandas opentrons openpyxl
```

## Usage

Run the application using:

```sh
streamlit run protogen.py
```

## UI Overview

### 1. File Upload (Input File Format)
Protogen uses Excel files (`.xlsx`) as input. Each sheet should contain a 96-well plate format table where each cell represents a well and contains the component name at that position. Example:

|    | A  | B  | C  | ...|
|----|----|----|----|----|
| 1  | (P)1 | (C)1 | (T)1 |    |
| 2  | (P)2 | (C)2 | (T)2 |    |
| 3  | (P)3 | (C)3 | (T)3 |    |
| ...|

- Each well (A1, B1, C1, etc.) contains a component name (e.g., Promoter, CDS, Terminator).
- Empty cells indicate unused wells.
- Plate names and components are mapped automatically.

### 2. Plate & Volume Settings
- Set plate names from the uploaded file.
- Configure default volumes for each well.
- Automatically assign initial volumes to components.

### 3. Lv1 Assembly Design
#### Inputs
- **Group Setup**: Define groups containing transcription units (TUs).
- **TU Design**: Select Promoter, CDS, Terminator, and Connector.
- **Volume Configuration**: Specify the volume used per component in each TU.
- **Common Reagents**: Add common reagents such as GGAmix.

#### Calculation Process
- Extract required components from the uploaded plate and generate assembly combinations.
- Calculate the required volume for each component and determine the minimum batch size.
- If total volume exceeds 50µL, distribute into multiple batches accordingly.

### 4. Lv2 Assembly Design
#### Inputs
- **TU List from Lv1 Output**
- **Lv2 Volume Configuration**: Define required volume per TU and dead volume.
- **Additional Common Reagents**: Add additional reagents such as vectors.

#### Calculation Process
- Track TU usage from Lv1 and generate non-overlapping combinations for groups.
- Determine the number of times each TU is used and calculate required volume.
- Determine total preparation requirements for the experiment.

### 5. Protocol Generation & Output Files
- **Select OT-2 or Janus**: Choose the robotic system to use.
- **Auto-generate Protocols**: Generate OT-2 or Janus protocols based on user settings.
- **Review Outputs**: Verify the final well locations and reagent usage details.

## Output Files

- **OT-2 Protocol**: A Python script formatted for Opentrons.
- **Janus Protocol**: A structured CSV file for Hamilton Janus.
- **Updated Stock Information**: A DataFrame with updated volume calculations.

## Example Workflow

1. Upload your `plate_sample.xlsx` file.
2. Set up well positions and default volume values.
3. Define TU and group settings.
4. Review the volume calculations.
5. Select OT-2 or Janus and generate protocols.
6. Save and run the generated protocol on your robotic system.

## Troubleshooting

- If the program warns about insufficient volume, check and update stock volumes in the Excel file.
- If OT-2 scripts fail, verify API compatibility (e.g., `apiLevel: 2.17`).
- Ensure correct plate definitions in your OT-2 setup.

## License

This project is licensed under the MIT License.

## Contributing

Feel free to submit issues or pull requests to improve the tool!

---

Developed for laboratory automation workflows.

