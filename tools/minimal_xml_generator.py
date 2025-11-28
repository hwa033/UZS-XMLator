"""
Minimal XML generator tool.

This script provides three minimal functions:
 - read_input(input_path): read JSON or CSV input or return sample data
 - generate_xml(data): build an XML Element from a fixed template
 - save_and_log(element, out_dir): save the XML to a timestamped file and log the result

No external dependencies; uses only Python standard library.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET


def read_input(input_path: Optional[str] = None) -> List[Dict[str, str]]:
    """Read input data from JSON or CSV file. If no path is provided,
    return a small sample dataset so non-technical users can run the tool immediately.

    Expected format for JSON: a list of objects, e.g. [{"name": "A", "value": "1"}, ...]
    Expected CSV: header row with columns matching keys, each following row is a record.
    """
    if not input_path:
        # Return a simple, safe default dataset
        return [
            {"id": "1", "name": "Alice", "amount": "100.00"},
            {"id": "2", "name": "Bob", "amount": "250.50"},
        ]

    input_path = os.path.abspath(input_path)
    if input_path.lower().endswith(".json"):
        with open(input_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            # Ensure we always return a list of dicts
            if isinstance(data, dict):
                return [data]
            return list(data)

    if input_path.lower().endswith(".csv"):
        with open(input_path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return [row for row in reader]

    raise ValueError("Unsupported input format. Provide a .json or .csv file, or omit the argument to use sample data.")


def generate_xml(records: List[Dict[str, str]]) -> ET.Element:
    """Generate an XML Element tree using a fixed template.

    Template structure:
      <Envelope>
        <Header>
          <GeneratedAt>...</GeneratedAt>
          <RecordCount>...</RecordCount>
        </Header>
        <Body>
          <Item>
            <FieldName>value</FieldName>
            ...
          </Item>
          ...
        </Body>
      </Envelope>

    Each record becomes one <Item> with children for each key.
    """
    envelope = ET.Element("Envelope")

    header = ET.SubElement(envelope, "Header")
    generated_at = ET.SubElement(header, "GeneratedAt")
    generated_at.text = datetime.utcnow().isoformat() + "Z"
    count = ET.SubElement(header, "RecordCount")
    count.text = str(len(records))

    body = ET.SubElement(envelope, "Body")
    for rec in records:
        item = ET.SubElement(body, "Item")
        # Keep stable ordering by sorting keys so output is predictable
        for key in sorted(rec.keys()):
            elem = ET.SubElement(item, key)
            # Convert values to strings; None -> empty string
            value = rec.get(key, "")
            elem.text = "" if value is None else str(value)

    return envelope


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Simple pretty-printer for ElementTree (in-place)."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def save_and_log(element: ET.Element, out_dir: str = "output") -> str:
    """Save the XML Element to a timestamped file under out_dir and append a small log entry.

    Returns the path to the saved XML file.
    """
    os.makedirs(out_dir, exist_ok=True)
    # Timestamp filename for uniqueness and easy sorting
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_{ts}.xml"
    path = os.path.join(out_dir, filename)

    # Pretty-print then write as UTF-8 with XML declaration
    _indent(element)
    tree = ET.ElementTree(element)
    try:
        tree.write(path, encoding="utf-8", xml_declaration=True)
        status = "SUCCESS"
    except Exception as exc:  # Keep minimal error handling and surface the issue
        status = f"FAIL: {exc}"

    # Write a simple append-only log (human readable)
    logs_dir = os.path.join(os.path.dirname(path), "..", "logs")
    logs_dir = os.path.abspath(logs_dir)
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "generator.log")
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"{datetime.utcnow().isoformat()}Z\t{os.path.abspath(path)}\t{status}\n")

    if status.startswith("SUCCESS"):
        return path
    raise RuntimeError(status)


def main():
    parser = argparse.ArgumentParser(description="Minimal XML generator (standard library only)")
    parser.add_argument("--input", help="Path to input .json or .csv file (optional)")
    parser.add_argument("--outdir", default="build/minimal_xml_output", help="Directory where XML and logs are saved")
    args = parser.parse_args()

    try:
        data = read_input(args.input)
        element = generate_xml(data)
        saved = save_and_log(element, args.outdir)
        print(f"XML generated and saved to: {saved}")
    except Exception as exc:
        print(f"Generation failed: {exc}")
        raise


if __name__ == "__main__":
    main()
