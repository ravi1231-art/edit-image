from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_path
import os
import shutil
import uuid

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with your frontend URL for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
POPPLER_PATH = r"C:\Users\chaud\Downloads\Release-24.08.0-0 (1)\poppler-24.08.0\Library\bin"
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Function to delete temporary file
def delete_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@app.post("/convert-pdf/")
async def convert_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    # ✅ 1. Check if file is a valid PDF
    if file.content_type != "application/pdf":
        return {"error": "Invalid file type. Please upload a PDF file."}

    # ✅ 2. Save uploaded PDF to disk
    temp_pdf_name = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(OUTPUT_FOLDER, temp_pdf_name)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ 3. Convert first page of PDF to image
    images = convert_from_path(pdf_path, dpi=400, poppler_path=POPPLER_PATH)
    image_filename = f"{uuid.uuid4()}.png"
    image_path = os.path.join(OUTPUT_FOLDER, image_filename)
    images[0].save(image_path, "PNG")

    # ✅ 4. Delete temporary PDF file
    delete_file(pdf_path)

    # ✅ 5. Schedule deletion of output image after sending response
    background_tasks.add_task(delete_file, image_path)

    # ✅ 6. Return image file as response
    return FileResponse(image_path, media_type="image/png", filename=image_filename)

from fastapi import Request
from fastapi.responses import StreamingResponse
from PIL import Image
import base64
from io import BytesIO

@app.post("/save-edited-image/")
async def save_edited_image(request: Request):
    data = await request.json()
    image_data = data["image_data"]

    # Decode Base64 image
    header, encoded = image_data.split(",", 1)
    decoded_bytes = base64.b64decode(encoded)
    image = Image.open(BytesIO(decoded_bytes)).convert("RGB")  # ✅ Convert to 24-bit RGB

    # Ensure image size is correct (match 800 DPI A4 conversion)
    expected_width = 3306
    expected_height = 4678
    if image.size != (expected_width, expected_height):
        image = image.resize((expected_width, expected_height), resample=Image.NEAREST)

    # Save to buffer with PNG compression and correct DPI
    output_buffer = BytesIO()
    image.save(output_buffer, format="PNG", dpi=(400, 400))  # ✅ No need to set optimize/compress_level
    output_buffer.seek(0)

    return StreamingResponse(output_buffer, media_type="image/png")