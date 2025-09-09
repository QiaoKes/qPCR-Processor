# qPCR-Processor

[English Documentation](README.md) | [中文文档](README_CN.md)

A Python-based tool for processing qPCR (Quantitative Polymerase Chain Reaction) experimental data. This processor reads raw qPCR data from Excel files, performs normalization calculations using reference genes, and generates formatted output with charts.

## Features

- Automated reading of qPCR data from Excel files (.xls/.xlsx)
- Sample name mapping to experiment names
- Normalization using reference genes (GAPDH, TBP by default)
- Error detection and alerting based on standard deviation thresholds
- Automatic generation of bar charts in Excel output
- Comprehensive logging for debugging and monitoring

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Installation Steps

1. Clone or download this repository to your local machine.

2. Navigate to the project directory:
   ```bash
   cd qPCR-Processor
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

   Or use the provided installation scripts:
   - **Windows**: Double-click `install-win.bat`
   - **macOS/Linux**: Run `./install-mac-linux.sh`

## Usage

### Running the Processor

1. Place your qPCR data files in the `src_data/` directory following the naming convention (see below).

2. Configure the sample mapping in `config/sample_mapping.json` if needed.

3. Run the processor:
   ```bash
   python src/main.py
   ```

   Or use the provided startup scripts:
   - **Windows**: Double-click `start-win.bat`
   - **macOS/Linux**: Run `./start-mac-linux.sh`

4. Check the output files in the `dst_data/` directory (created automatically).

5. View logs in `experiment_processor.log` for processing details.

### File Naming Convention

Input Excel files in `src_data/` must follow this format:
```
{Prefix} {Date} {Time}.xls
```

Examples:
- `P1 2025-07-28 160758.xls`
- `P2 1999-01-02 237342.xls`

The **prefix** (part before the first space) is used to map samples to experiment names in `config/sample_mapping.json`.

### Excel File Format

- **Sheet Name**: Must contain a sheet named "Results"
- **Data Structure**: The processor will automatically skip invalid header rows and extract the following columns:
  - `Experiment Name`
  - `Well Position`
  - `Target Name`
  - `Sample Name`
  - `CT` (Cycle Threshold values)

## Configuration

### sample_mapping.json Fields

The `config/sample_mapping.json` file contains several important configuration sections:

#### `sample_mapping`
Maps sample names to experiment names, grouped by file prefix:
```json
{
  "P1": {
    "1": "E01",
    "2": "E02",
    ...
  },
  "P2": {
    "1": "E13",
    "2": "E14",
    ...
  }
}
```
- **File Prefix**: The part before the first space in the filename (e.g., "P1" from "P1 2025-07-28 160758.xls")
- **Sample Name**: Original sample identifier in the Excel file
- **Experiment Name**: Experiment identifier (E01-E24) used in output for de-identification

#### `reference_genes`
List of reference genes for normalization:
```json
["GAPDH", "TBP"]
```
Add more reference genes like "ACTB" if needed.

#### `error_threshold`
Threshold for error alerts (standard deviation as multiple of mean):
```json
0.3
```
Alerts when SD > 30% of mean value.

#### `chart_layout`
Layout parameters for Excel bar charts:
- `start_col`: Starting column for charts (Excel column index)
- `chart_width`/`chart_height`: Plot area dimensions
- `window_width`/`window_height`: Total chart window size
- `plot_area_left_margin`: Left margin ratio for plot area
- `bar_color`: Hex color code for bars (e.g., "4472C4" for blue)
- `grid_line_color`: Hex color code for grid lines (e.g., "D3D3D3" for light gray)

## Output

- Processed data files with normalization calculations
- Bar charts for each target gene
- Error alerts for data points exceeding thresholds
- Comprehensive processing logs

## Troubleshooting

- Check `experiment_processor.log` for detailed error messages
- Ensure Excel files have a "Results" sheet with required columns
- Verify file naming follows the specified convention
- Confirm sample mapping configuration matches your data

## License

See LICENSE file for details.
