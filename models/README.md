Marking Detection FastAPI service

Setup

1. Create a Python 3.10/3.11 virtual environment and activate it:

   python3 -m venv .venv
   source .venv/bin/activate

2. Install dependencies:

   pip install -r requirements.txt

   If you need the Roboflow / inference sdk, install a compatible pinned version, for example:

   pip install inference-sdk==0.9.23

3. Set your `roboflow_api_key` in a `.env` file next to `app.py` or in your environment:

   ROBOFLOW_API_KEY=your_key_here

Run

Start the server (from `backend/`):

   uvicorn app:app --reload --host 0.0.0.0 --port 8000

Endpoints
- GET /health
- POST /run (form fields: workspace_name, workflow_id, optional image_file upload or image_path URL)
- GET /output_image
- GET /detected_text
