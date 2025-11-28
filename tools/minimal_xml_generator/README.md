# Minimal XML generator

This is a tiny, dependency-free XML generator intended for non-technical users.

Usage

- Run with sample data (no dependencies):

```powershell
python tools/minimal_xml_generator.py
```

- Run with a JSON input file (list of objects):

```powershell
python tools/minimal_xml_generator.py --input tools/sample_input.json
```

- Run with a CSV input file (header row required):

```powershell
python tools/minimal_xml_generator.py --input tools/sample_input.csv
```

Where files are saved

- XML files: `build/minimal_xml_output/` (timestamped filenames)
- Logs: `build/logs/generator.log` (append-only; records timestamp, generated file path, and status)

Notes

- Only uses the Python standard library (`xml.etree.ElementTree`, `datetime`, `os`, etc.).
- The script intentionally keeps behavior simple: it reads input, writes XML, and logs success/failure.
- If you want to change the XML structure, edit `generate_xml()` in `tools/minimal_xml_generator.py`.
