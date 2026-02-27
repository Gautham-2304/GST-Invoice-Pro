import pandas as pd
from typing import List
from processor import InvoiceData

def safe_float(value):
    if value is None: return 0.0
    try:
        if isinstance(value, (int, float)): return float(value)
        # Remove commas, spaces, currency symbols
        clean_v = str(value).replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
        return float(clean_v) or 0.0
    except:
        return 0.0

def generate_gstr1_csv(data_list: List[InvoiceData], output_path: str):
    print(f"DEBUG EXPORT: Found {len(data_list)} invoices to export to CSV.")
    rows = []
    for i, data in enumerate(data_list):
        print(f"DEBUG EXPORT: Processing row {i+1}: Inv={data.invoice_number}, Total={data.total_amount}")
        rows.append({
            "Recipient GSTIN": data.gstin,
            "Invoice Number": data.invoice_number,
            "Invoice Date": data.date,
            "Invoice Value": safe_float(data.total_amount),
            "Place Of Supply": "00-Other Territory",
            "Reverse Charge": "N",
            "Invoice Type": "Regular",
            "E-Commerce GSTIN": "",
            "Rate": safe_float(data.rate),
            "Taxable Value": safe_float(data.taxable_value),
            "Cess Amount": 0.0
        })
    
    df = pd.DataFrame(rows)
    print(f"DEBUG EXPORT: Final DataFrame has {len(df)} rows. Saving to {output_path}")
    df.to_csv(output_path, index=False)
    return output_path

def generate_gstr1_excel(invoices: List[InvoiceData], output_path: str):
    print(f"DEBUG EXPORT: Found {len(invoices)} invoices to export to EXCEL.")
    data = []
    for i, inv in enumerate(invoices):
        print(f"DEBUG EXPORT: Processing row {i+1}: Inv={inv.invoice_number}, Total={inv.total_amount}")
        data.append({
            "GSTIN/UIN of Recipient": inv.gstin,
            "Invoice Number": inv.invoice_number,
            "Invoice date": inv.date,
            "Invoice Value": safe_float(inv.total_amount),
            "Place Of Supply": "36-Telangana",
            "Reverse Charge": "N",
            "Invoice Type": "Regular",
            "Rate": safe_float(inv.rate),
            "Taxable Value": safe_float(inv.taxable_value),
            "Integrated Tax": safe_float(inv.igst),
            "Central Tax": safe_float(inv.cgst),
            "State/UT Tax": safe_float(inv.sgst),
            "Cess": 0.0
        })
    
    df = pd.DataFrame(data)
    print(f"DEBUG EXPORT: Final DataFrame has {len(df)} rows. Saving to {output_path}")
    df.to_excel(output_path, index=False, engine='openpyxl')
    return output_path
