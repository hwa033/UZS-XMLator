"""
Extract UwvZwMeldingInternBody from SOAP envelope.

This tool strips the SOAP-ENV:Envelope wrapper and outputs only the
body content (UwvZwMeldingInternBody element) which is what some
systems expect for direct upload.
"""
import sys
from pathlib import Path
from lxml import etree

def extract_body_from_soap(input_path: str, output_path: str = None) -> str:
    """
    Extract the UwvZwMeldingInternBody from SOAP envelope.
    
    Args:
        input_path: Path to the SOAP XML file
        output_path: Optional output path. If None, uses input_path with '_body' suffix
    
    Returns:
        Path to the extracted body XML file
    """
    tree = etree.parse(input_path)
    root = tree.getroot()
    
    # Find the SOAP Body element
    ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
    body = root.find('.//soap:Body', ns)
    
    if body is None:
        raise ValueError("No SOAP Body found in XML")
    
    # Get the first child of Body (should be UwvZwMeldingInternBody)
    body_content = None
    for child in body:
        body_content = child
        break
    
    if body_content is None:
        raise ValueError("No content found in SOAP Body")
    
    # Determine output path
    if output_path is None:
        input_p = Path(input_path)
        output_path = str(input_p.parent / f"{input_p.stem}_body{input_p.suffix}")
    
    # Write just the body content as root element
    output_tree = etree.ElementTree(body_content)
    output_tree.write(
        output_path,
        pretty_print=True,
        xml_declaration=True,
        encoding='UTF-8'
    )
    
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_body_from_soap.py <input_soap_xml> [output_xml]")
        print("\nExtracts UwvZwMeldingInternBody from SOAP envelope for direct system upload.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = extract_body_from_soap(input_file, output_file)
        print(f"Extracted body to: {result}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
