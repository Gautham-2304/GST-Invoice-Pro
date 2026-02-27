import os
import google.generativeai as genai
from PIL import Image
import json
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Models precisely matched from your environment's list
MODELS_TO_TRY = [
    'models/gemini-2.0-flash',
    'models/gemini-2.5-flash',
    'models/gemini-flash-latest',
    'models/gemini-2.0-flash-lite',
    'models/gemini-flash-lite-latest',
    'models/gemini-2.5-pro'
]

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

from pydantic import BaseModel, field_validator

class InvoiceData(BaseModel):
    gstin: Optional[str] = ""
    invoice_number: Optional[str] = ""
    date: Optional[str] = ""
    total_amount: Optional[float] = 0.0
    taxable_value: Optional[float] = 0.0
    igst: Optional[float] = 0.0
    cgst: Optional[float] = 0.0
    sgst: Optional[float] = 0.0
    rate: Optional[float] = 0.0

    @field_validator('total_amount', 'taxable_value', 'igst', 'cgst', 'sgst', 'rate', mode='before')
    @classmethod
    def clean_numeric(cls, v):
        if v is None: return 0.0
        if isinstance(v, (int, float)): return float(v)
        try:
            # Remove currency symbols, commas, and spaces
            clean_v = str(v).replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
            return float(clean_v)
        except:
            return 0.0

def extract_invoice_data(file_path: str) -> InvoiceData:
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        uploaded_file = genai.upload_file(file_path, mime_type='application/pdf')
        import time
        while genai.get_file(uploaded_file.name).state.name != "ACTIVE":
            time.sleep(1)
        content_part = uploaded_file
    else:
        content_part = Image.open(file_path)

    prompt = """
    Analyze this invoice and extract the details in JSON format.
    The invoice can be handwritten, computer-generated, or even a slightly blurred photo.
    
    Fields to extract:
    - gstin (GST Number of supplier)
    - invoice_number
    - date (DD-MM-YYYY)
    - total_amount
    - taxable_value
    - igst, cgst, sgst
    - rate (primary GST rate, e.g., 18.0)

    If handwritten or blurred, use your high-level visual reasoning to decipher the text and numbers.
    Return ONLY valid JSON.
    """

    import time
    last_error = ""
    
    for model_name in MODELS_TO_TRY:
        max_retries = 2
        retry_delay = 5 

        for attempt in range(max_retries):
            try:
                print(f"DEBUG: Attempting with {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([prompt, content_part])
                
                # If we get here, it worked!
                text = response.text.strip()
                # Clean JSON markers if present
                if text.startswith("```json"):
                    text = text[7:-3].strip()
                elif text.startswith("```"):
                    text = text[3:-3].strip()
                    
                data = json.loads(text)
                return InvoiceData(**data)

            except Exception as e:
                last_error = str(e)
                if "429" in last_error:
                    print(f"DEBUG: 429 Quota on {model_name}. Attempt {attempt+1}/{max_retries}. Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                elif "404" in last_error:
                    print(f"DEBUG: 404 on {model_name}. Skipping to next model...")
                    break # Try next model in list
                else:
                    raise e
        
        print(f"DEBUG: Moving to next model due to persistent issues with {model_name}")

    # If we exhausted all models
    raise Exception(f"All available models reached their daily quota or failed. Last error: {last_error}")
