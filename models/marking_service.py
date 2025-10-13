from inference_sdk import InferenceHTTPClient
from dotenv import load_dotenv
import os
import base64
from typing import Dict, Any, Optional, Tuple

load_dotenv()

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=os.getenv("roboflow_api_key")
)


def _find_values_by_key(obj, search_key):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == search_key:
                found.append(v)
            found.extend(_find_values_by_key(v, search_key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_values_by_key(item, search_key))
    return found


def _find_all_text_fields(obj):
    res = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and isinstance(v, str):
                res.append(v)
            else:
                res.extend(_find_all_text_fields(v))
    elif isinstance(obj, list):
        for item in obj:
            res.extend(_find_all_text_fields(item))
    return res


def run_workflow_and_save(
    image: Dict[str, str],
    out_dir: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Run the Roboflow workflow and save the output image (first found) and detected text.

    Returns (image_path, text_path, raw_result)
    """
    if out_dir is None:
        out_dir = os.path.dirname(__file__)

    result = CLIENT.run_workflow(
    workspace_name="yuktha-ailil",
    workflow_id="detect-count-and-visualize-4",
    images={
        "image": image['image']
    },
    use_cache=True
    )

    # Save image
    output_images = _find_values_by_key(result, "output_image")
    image_path = None
    if output_images:
        img_b64 = output_images[0]
        try:
            img_bytes = base64.b64decode(img_b64)
            image_path = os.path.join(out_dir, "workflow_output.jpg")
            with open(image_path, "wb") as f:
                f.write(img_bytes)
        except Exception:
            image_path = None

    # Extract text
    texts = set()
    if isinstance(result, dict):
        for k, v in result.items():
            if k.startswith("google_vision_ocr") and isinstance(v, dict):
                txt = v.get("text")
                if isinstance(txt, str) and txt.strip():
                    texts.add(txt.strip())

    for t in _find_all_text_fields(result):
        if t and t.strip():
            texts.add(t.strip())

    detected_text = "\n\n".join(sorted(texts)) if texts else ""
    text_path = os.path.join(out_dir, "detected_text.txt")
    try:
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(detected_text)
    except Exception:
        text_path = None

    return image_path, text_path, result
