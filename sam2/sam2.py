"""
IC Pin Counter using SAM 2 (Segment Anything Model 2)
"""

import os
import argparse
import numpy as np
from PIL import Image
import torch
from sam2.build_sam import build_sam2
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
from huggingface_hub import hf_hub_download


def download_model(model_size: str = "large"):
    """Download SAM2 checkpoint from HuggingFace."""
    model_map = {
        "tiny": ("facebook/sam2-hiera-tiny", "sam2_hiera_tiny.pt", "sam2_hiera_t.yaml"),
        "small": ("facebook/sam2-hiera-small", "sam2_hiera_small.pt", "sam2_hiera_s.yaml"),
        "base": ("facebook/sam2-hiera-base-plus", "sam2_hiera_base_plus.pt", "sam2_hiera_b+.yaml"),
        "large": ("facebook/sam2-hiera-large", "sam2_hiera_large.pt", "sam2_hiera_l.yaml"),
    }

    repo_id, checkpoint_name, config_name = model_map[model_size]

    checkpoint_path = hf_hub_download(
        repo_id=repo_id,
        filename=checkpoint_name,
    )

    return checkpoint_path, config_name


def load_sam2_model(model_size: str = "large"):
    """Load SAM2 model."""
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"Using device: {device}")

    print(f"Loading SAM2 {model_size}...")
    checkpoint_path, config_name = download_model(model_size)

    sam2_model = build_sam2(config_name, checkpoint_path, device=device)

    mask_generator = SAM2AutomaticMaskGenerator(
        model=sam2_model,
        points_per_side=32,
        pred_iou_thresh=0.7,
        stability_score_thresh=0.92,
        min_mask_region_area=100,
    )

    print("Model loaded!")
    return mask_generator


def count_pins(mask_generator, image: Image.Image) -> int:
    """Count IC pins by filtering segmented masks."""
    image_np = np.array(image)
    height, width = image_np.shape[:2]

    print("Generating masks...")
    masks = mask_generator.generate(image_np)
    print(f"Found {len(masks)} total segments")

    # Filter for pin-like masks
    pin_count = 0
    for mask in masks:
        area = mask['area']
        bbox = mask['bbox']  # x, y, w, h

        # Pins are small relative to image
        if area < 50 or area > (width * height * 0.05):
            continue

        # Pins are at top or bottom edges (for DIP packages)
        center_y = bbox[1] + bbox[3] / 2
        is_edge = (center_y < height * 0.3) or (center_y > height * 0.7)

        if is_edge:
            pin_count += 1

    return pin_count


def main():
    parser = argparse.ArgumentParser(description="Count Integrated Circuit pins using SAM2")
    parser.add_argument("image_path", type=str, help="Path to IC image")
    parser.add_argument("--model-size", type=str, default="large",
                       choices=["tiny", "small", "base", "large"],
                       help="SAM2 model size")
    args = parser.parse_args()

    image = Image.open(args.image_path).convert("RGB")
    mask_generator = load_sam2_model(args.model_size)

    pin_count = count_pins(mask_generator, image)

    print(f"\nPin Count: {pin_count}")


if __name__ == "__main__":
    main()
