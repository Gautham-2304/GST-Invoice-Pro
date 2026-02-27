from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import shutil
from processor import extract_invoice_data, InvoiceData
from exporter import generate_gstr1_csv, generate_gstr1_excel
import uuid

app = FastAPI()
print("DEBUG: SERVER STARTING - STABILITY FIX V4 ACTIVE")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
EXPORT_DIR = "exports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

@app.post("/api/upload")
async def upload_invoices(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            data = extract_invoice_data(file_path)
            results.append({"filename": file.filename, "data": data.dict(), "status": "success"})
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e), "status": "failed"})
    
    return results

@app.post("/api/export")
async def export_data(requestBody: dict):
    invoices = requestBody.get('invoices', [])
    export_format = requestBody.get('format', 'csv')
    
    print(f"DEBUG EXPORT: Received {len(invoices)} invoices for export preparation")
    
    if not invoices:
        raise HTTPException(status_code=400, detail="No invoice data provided")
    
    data_list = []
    for inv in invoices:
        inner_data = inv.get('data')
        if inner_data:
            try:
                data_list.append(InvoiceData(**inner_data))
            except Exception as e:
                print(f"ERROR: Failed to parse invoice data: {e}")
                continue
    
    if not data_list:
        raise HTTPException(status_code=400, detail="No valid invoice data found to export")
    
    # Generate a unique file ID
    file_id = uuid.uuid4().hex
    ext = "xlsx" if export_format == "excel" else "csv"
    filename = f"GSTR1_Report_{file_id[:8]}.{ext}"
    export_path = os.path.join(EXPORT_DIR, filename)
    
    if export_format == 'excel':
        generate_gstr1_excel(data_list, export_path)
    else:
        generate_gstr1_csv(data_list, export_path)
    
    print(f"DEBUG EXPORT: File prepared: {filename}")
    return {"status": "success", "file_id": filename}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Map extension to media type
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if filename.endswith('.xlsx') else 'text/csv'
    
    # Content-Disposition: attachment; filename="..." is the key for browser naming
    return FileResponse(
        file_path, 
        media_type=media_type, 
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
