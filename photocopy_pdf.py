#!/usr/bin/env python3
"""
photocopy_pdf.py

Take a folder of JPEG photos of documents (e.g. shot with a phone) and
export a "photocopy style" PDF for each one — either a modern grayscale
scan look (default) or a stark black-and-white look.

Usage:
    python photocopy_pdf.py -i /path/to/jpegs -o /path/to/pdfs

Optional tuning:
    --mode grayscale   'grayscale' (default, realistic modern-copier look
                        with soft gray tones) or 'bw' (stark binary black/white)
    --contrast 1.3     Grayscale mode only: contrast multiplier
    --brightness 10    Grayscale mode only: brightness offset (-255 to 255)
    --block-size 25   BW mode only: size of the local region used for adaptive
                       thresholding (must be odd; bigger = smoother, smaller = more detail/noise)
    --c 15             BW mode only: constant subtracted from the local mean threshold.
                       Higher = more aggressive black/white split (whiter background)
    --denoise          Apply denoising before conversion (slower, cleans up phone noise)
    --dpi 300          DPI written into the output PDF (affects perceived print size)
    --no-perspective   Skip automatic page-edge detection / deskewing
    --no-rotate        Skip automatic rotation of landscape pages to portrait

Requirements:
    pip install opencv-python-headless numpy pillow
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

VALID_EXTS = {".jpg", ".jpeg"}


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left has smallest x+y
    rect[2] = pts[np.argmax(s)]  # bottom-right has largest x+y
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right has smallest y-x
    rect[3] = pts[np.argmax(diff)]  # bottom-left has largest y-x
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Warp the quadrilateral defined by pts into a flat, front-on rectangle."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )

    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, m, (max_width, max_height))


def find_document_contour(img_bgr: np.ndarray):
    """
    Try to find the page's 4 corners in the photo. Returns a (4, 2) array of
    points in the ORIGINAL image's coordinate space, or None if no confident
    quadrilateral was found.
    """
    orig_h, orig_w = img_bgr.shape[:2]

    # Work on a downscaled copy for speed and more stable edge detection.
    scale = 800.0 / orig_h
    small = cv2.resize(img_bgr, (int(orig_w * scale), int(orig_h * scale)))

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 50, 150)
    edged = cv2.dilate(edged, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    small_area = small.shape[0] * small.shape[1]
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.2 * small_area:
            pts = approx.reshape(4, 2).astype("float32")
            return pts / scale  # scale back up to original image coordinates

    return None


def make_bw_photocopy(img_bgr: np.ndarray, block_size: int, c: int, denoise: bool) -> np.ndarray:
    """Convert a BGR image array into a stark black-and-white 'photocopy' look."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # Improve local contrast so uneven lighting on the page doesn't cause
    # patchy thresholding (very typical with phone photos of documents).
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # block_size must be odd and >= 3
    if block_size % 2 == 0:
        block_size += 1
    block_size = max(block_size, 3)

    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )

    # Light cleanup of speckle noise left over from the threshold step.
    bw = cv2.medianBlur(bw, 3)

    return bw


def make_grayscale_photocopy(img_bgr: np.ndarray, denoise: bool, contrast: float, brightness: int) -> np.ndarray:
    """
    Convert a BGR image array into a soft grayscale 'modern photocopier' look:
    an evenly-lit, near-white background with natural gray shading preserved
    in text and images (rather than a stark black/white split).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # Estimate and flatten uneven lighting/shadows across the page so the
    # background becomes an even near-white, the way a copier's light bar does.
    dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
    background = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, background)
    flattened = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # Push contrast/brightness so the background reads as white while
    # keeping soft gray tones in text edges and any photos/shading.
    adjusted = cv2.convertScaleAbs(flattened, alpha=contrast, beta=brightness)

    # Light unsharp mask for crisper, copier-like text edges.
    blurred = cv2.GaussianBlur(adjusted, (0, 0), sigmaX=3)
    sharpened = cv2.addWeighted(adjusted, 1.5, blurred, -0.5, 0)

    return sharpened


def rotate_to_portrait(img_bgr: np.ndarray) -> np.ndarray:
    """If the image is wider than it is tall, rotate it 90° so it's portrait."""
    h, w = img_bgr.shape[:2]
    if w > h:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
    return img_bgr


def process_folder(input_dir: Path, output_dir: Path, mode: str, block_size: int, c: int,
                    contrast: float, brightness: int, denoise: bool, dpi: int,
                    perspective: bool, auto_rotate: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VALID_EXTS
    )

    if not files:
        print(f"No JPEG files found in {input_dir}")
        return

    for path in files:
        img_bgr = cv2.imread(str(path))
        if img_bgr is None:
            print(f"  ! Skipping {path.name} (could not read image)")
            continue

        if perspective:
            corners = find_document_contour(img_bgr)
            if corners is not None:
                img_bgr = four_point_transform(img_bgr, corners)
            else:
                print(f"  i {path.name}: no clear page edges found, using original framing")

        if auto_rotate:
            img_bgr = rotate_to_portrait(img_bgr)

        if mode == "bw":
            result = make_bw_photocopy(img_bgr, block_size=block_size, c=c, denoise=denoise)
        else:
            result = make_grayscale_photocopy(img_bgr, denoise=denoise, contrast=contrast, brightness=brightness)

        pil_img = Image.fromarray(result)  # single-channel 'L' mode image
        out_path = output_dir / (path.stem + ".pdf")
        pil_img.save(out_path, "PDF", resolution=dpi)

        print(f"  ✓ {path.name} -> {out_path.name}")

    print(f"\nDone. {len(files)} file(s) processed into {output_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input", required=True, help="Folder containing JPEG photos")
    parser.add_argument("-o", "--output", required=True, help="Folder to write PDFs into")
    parser.add_argument("--mode", choices=["grayscale", "bw"], default="grayscale",
                         help="'grayscale' for a realistic modern-copier look (default), 'bw' for stark black/white")
    parser.add_argument("--contrast", type=float, default=1.3, help="Grayscale mode: contrast multiplier (default 1.3)")
    parser.add_argument("--brightness", type=int, default=10, help="Grayscale mode: brightness offset, -255 to 255 (default 10)")
    parser.add_argument("--block-size", type=int, default=25, help="BW mode: adaptive threshold block size (odd number, default 25)")
    parser.add_argument("--c", type=int, default=15, help="BW mode: threshold constant C (default 15, higher = whiter background)")
    parser.add_argument("--denoise", action="store_true", help="Apply denoising before conversion")
    parser.add_argument("--dpi", type=int, default=300, help="DPI to embed in output PDF (default 300)")
    parser.add_argument("--no-perspective", action="store_true", help="Skip automatic page-edge detection / deskewing")
    parser.add_argument("--no-rotate", action="store_true", help="Skip automatic rotation of landscape pages to portrait")
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not input_dir.is_dir():
        print(f"Error: input folder does not exist: {input_dir}")
        sys.exit(1)

    process_folder(
        input_dir=input_dir,
        output_dir=output_dir,
        mode=args.mode,
        block_size=args.block_size,
        c=args.c,
        contrast=args.contrast,
        brightness=args.brightness,
        denoise=args.denoise,
        dpi=args.dpi,
        perspective=not args.no_perspective,
        auto_rotate=not args.no_rotate,
    )


if __name__ == "__main__":
    main()