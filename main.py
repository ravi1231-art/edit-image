from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import fitz  # PyMuPDF
import os
import uuid
import shutil
import base64
from io import BytesIO

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def delete_file(path: str):
    if os.path.exists(path):
        os.remove(path)


@app.post("/convert-pdf/")
async def convert_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    if file.content_type != "application/pdf":
        return {"error": "Invalid file type. Please upload a PDF."}

    # Save the uploaded PDF
    pdf_id = str(uuid.uuid4())
    pdf_path = os.path.join(OUTPUT_FOLDER, f"{pdf_id}.pdf")
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Convert first page to image
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=400)
    image_path = os.path.join(OUTPUT_FOLDER, f"{pdf_id}.png")
    pix.save(image_path)

    # Clean up
    delete_file(pdf_path)
    background_tasks.add_task(delete_file, image_path)

    return FileResponse(image_path, media_type="image/png", filename=f"{pdf_id}.png")


@app.post("/save-edited-image/")
async def save_edited_image(request: Request):
    try:
        data = await request.json()
        image_data = data.get("image_data")
        if not image_data:
            return {"error": "Missing image_data"}

        header, encoded = image_data.split(",", 1)
        decoded = base64.b64decode(encoded)

        image = Image.open(BytesIO(decoded)).convert("RGB")
        image = image.resize((3306, 4678), Image.NEAREST)

        output_buffer = BytesIO()
        image.save(output_buffer, format="PNG", dpi=(400, 400))
        output_buffer.seek(0)

        return StreamingResponse(output_buffer, media_type="image/png")
    except Exception as e:
        return {"error": str(e)}
