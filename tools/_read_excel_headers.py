import json
import openpyxl

wb = openpyxl.load_workbook(r"D:/ZW/XML-automation-clean/docs/Input XML electr ziekmeldinge.xlsx", read_only=True)
ws = wb.active
headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
print(json.dumps(headers, ensure_ascii=False, indent=2))
