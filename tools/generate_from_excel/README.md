# Excel → SOAP XML generator

This script reads `docs/Input XML electr ziekmeldinge.xlsx` and produces SOAP-format XML messages compatible with the sample envelope in `docs/GAP3 v0428 Digipoort OTP3 MeldingZiekte - VOORBEELD.xml`.

Usage

- Bulk (single file with all messages):

```powershell
python tools/generate_from_excel.py --mode bulk
```

- Single (one file per Excel row):

```powershell
python tools/generate_from_excel.py --mode single
```

Options

- `--input` path to the Excel file (defaults to `docs/Input XML electr ziekmeldinge.xlsx`).
- `--outdir` directory where generated XML files will be saved (`build/excel_generated` by default).
- `--log` path to append log entries (`build/logs/generator_excel.log` by default).

Notes

- The script intentionally keeps mapping minimal and uses only `openpyxl` and the standard library for XML.
- The SOAP header is populated with generated identifiers and timestamps to follow the sample format.
- Excel formula results may appear in the output if the workbook contains formulas without saved cached values. To avoid formulas in output, save the workbook with computed values or export to CSV.
