from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import sys
from typing import Optional

# Ensure the backend folder is importable when uvicorn loads this module directly
THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from models.marking_service import run_workflow_and_save

app = FastAPI(title="Marking Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
async def run(
    image_file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
):
    """
    Run the Roboflow workflow.
    Provide either an uploaded file (`image_file`) or a path/URL in `image_path`.
    """
    out_dir = os.path.dirname(__file__)

    # decide image input
    if image_file is not None:
        upload_path = os.path.join(out_dir, image_file.filename)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        images = {"image": upload_path}
    elif image_path:
        images = {"image": image_path}
    else:
        raise HTTPException(status_code=400, detail="Provide image_file or image_path")

    image_path_saved, text_path_saved, raw = run_workflow_and_save(
        image=images,
        out_dir=out_dir,
    )

    return JSONResponse({
        "image_path": image_path_saved,
        "text_path": text_path_saved,
        "raw": raw,
    })


@app.get("/output_image")
def get_image():
    p = os.path.join(os.path.dirname(__file__), "workflow_output.jpg")
    if os.path.exists(p):
        return FileResponse(p, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Output image not found")


@app.get("/detected_text")
def get_text():
    p = os.path.join(os.path.dirname(__file__), "detected_text.txt")
    if os.path.exists(p):
        return FileResponse(p, media_type="text/plain")
    raise HTTPException(status_code=404, detail="Detected text not found")
