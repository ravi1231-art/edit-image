from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import os
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


from fastapi.responses import StreamingResponse
from io import BytesIO
import fitz  # PyMuPDF

@app.post("/convert-pdf/")
async def convert_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return {"error": "Invalid file type. Please upload a PDF."}

    # Read PDF file into memory
    pdf_bytes = await file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Convert first page to image
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=400)
    img_bytes = BytesIO()
    pix.save(img_bytes, format="png")
    img_bytes.seek(0)

    return StreamingResponse(img_bytes, media_type="image/png")


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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Serve static files from 'static' folder (you can change as needed)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root "/"
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Optional: Serve edit_screen.html
@app.get("/edit", response_class=HTMLResponse)
async def serve_edit_screen():
    with open("static/edit_screen.html", "r", encoding="utf-8") as f:
        return f.read()
