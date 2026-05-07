# Fix sample mapping numeric sample names

## Goal

Fix sample mapping so numeric `Sample Name` values read from Excel, such as `1.0`, correctly match JSON mapping keys such as `"1"`. This restores configured experiment names in processed output for files like `P1 ...xlsx` and `P2 ...xlsx`.

## What I already know

* `config/sample_mapping.json` uses nested file-prefix mappings: `{"P1": {"1": "..."}}`.
* `src/main.py` passes the extracted file prefix into `DataProcessor.apply_sample_mapping`.
* `DataReader.extract_file_prefix` extracts `P1` and `P2` correctly from current source filenames.
* The current source Excel files read `Sample Name` as `float64` values: `1.0` through `12.0`.
* Current mapping logic checks `1.0`, then `"1.0"`, but only normalizes numeric-looking strings to `"1"` when the original value is already a string.

## Requirements

* Map numeric Excel sample names like `1.0` to JSON keys like `"1"`.
* Preserve existing behavior for string sample names like `"1"`.
* Preserve existing behavior for already-mapped non-numeric sample names.
* Leave unmapped samples unchanged.
* Keep the change scoped to sample mapping logic and tests.

## Acceptance Criteria

* [ ] `Sample Name` value `1.0` maps through a config key `"1"`.
* [ ] `Sample Name` value `1` maps through a config key `"1"`.
* [ ] `Sample Name` value `"1"` maps through a config key `"1"`.
* [ ] Unmapped values remain unchanged.
* [ ] Existing tests pass.

## Definition of Done

* Tests added or updated for numeric sample name mapping.
* Relevant unit tests pass in the project virtual environment.
* No unrelated dirty files are modified.

## Out of Scope

* Changing the structure of `config/sample_mapping.json`.
* Renaming output sheets or changing Excel writing behavior.
* Installing or upgrading project dependencies.

## Technical Notes

* Primary file: `src/data_processor.py`.
* Existing tests: `test/test_data_processor.py`.
* Use `.venv/bin/python` for local verification because system `python3` lacks pandas.
