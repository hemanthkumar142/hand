"""Handwriting Analyzer Service for InkClone AI.

Extracts handwriting style metrics (slant, stroke width, spacing, baseline drift, ink color)
using OpenCV and Pillow.
"""

import io
from typing import Optional, Tuple
import cv2
import numpy as np
from PIL import Image

from config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    HandwritingStyleMetrics,
)


class HandwritingAnalyzer:
    """Analyzes a handwriting reference image to extract style parameters."""

    def __init__(self):
        pass

    def validate_image(self, file_bytes: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate file size and extension.
        
        Returns:
            (is_valid, error_message)
        """
        if not file_bytes:
            return False, "Uploaded file is empty."

        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return False, f"File size ({size_mb:.1f} MB) exceeds maximum limit of {MAX_FILE_SIZE_MB} MB."

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type (.{ext}). Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
        except Exception as e:
            return False, f"Invalid or corrupted image: {str(e)}"

        return True, None

    def analyze(self, file_bytes: bytes) -> HandwritingStyleMetrics:
        """Process image bytes and extract style metrics.
        
        Returns a HandwritingStyleMetrics instance.
        """
        # Load image via OpenCV
        nparr = np.frombuffer(file_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            # Fallback to defaults
            return HandwritingStyleMetrics(confidence_score=0.2)

        # Convert to RGB and Gray
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Preprocess: Denoise and adaptive/Otsu threshold
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # Background is usually light paper, ink is dark -> invert binary so ink is white (255)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological noise removal
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        clean_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        total_pixels = clean_mask.size
        ink_pixels = cv2.countNonZero(clean_mask)

        # Check if ink exists
        if ink_pixels < 100 or (ink_pixels / total_pixels) > 0.8:
            # Not enough text or image is mostly dark/noisy
            return HandwritingStyleMetrics(confidence_score=0.3)

        # 1. Analyze Slant Angle
        slant_deg = self._estimate_slant(clean_mask)

        # 2. Analyze Stroke Thickness
        stroke_width = self._estimate_stroke_thickness(clean_mask)

        # 3. Analyze Baseline Variance and Line Spacing
        line_spacing, baseline_var = self._estimate_baseline_and_line_spacing(clean_mask)

        # 4. Analyze Word and Character Spacing
        char_spacing, word_spacing = self._estimate_spacing(clean_mask)

        # 5. Extract Dominant Ink Color
        dominant_ink = self._extract_dominant_ink_color(img_rgb, clean_mask)

        # Confidence based on ink density and contour count
        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        num_components = len(contours)
        confidence = min(1.0, max(0.4, 0.4 + (num_components / 150.0) * 0.5))

        return HandwritingStyleMetrics(
            slant_angle=float(np.clip(slant_deg, -25.0, 25.0)),
            stroke_thickness=float(np.clip(stroke_width, 1.2, 4.5)),
            word_spacing=float(np.clip(word_spacing, 14.0, 36.0)),
            char_spacing=float(np.clip(char_spacing, -1.0, 6.0)),
            line_spacing=float(np.clip(line_spacing, 36.0, 60.0)),
            baseline_variance=float(np.clip(baseline_var, 0.5, 3.5)),
            dominant_ink_color=dominant_ink,
            confidence_score=round(float(confidence), 2),
        )

    def _estimate_slant(self, binary_mask: np.ndarray) -> float:
        """Estimate median letter slant using contour moments and oriented bounding boxes."""
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        angles = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            # Focus on tall vertical components like l, t, d, b, h
            if h > 20 and (h / max(w, 1)) > 1.2:
                # Compute central moments
                moments = cv2.moments(cnt)
                if moments["mu20"] != moments["mu02"]:
                    # Principal axis angle
                    theta = 0.5 * np.arctan2(2 * moments["mu11"], moments["mu20"] - moments["mu02"])
                    # Convert to degrees from vertical
                    deg = np.degrees(theta)
                    # Adjust to slant angle relative to vertical (0 = vertical)
                    slant = -(deg - 90) if deg > 0 else -(deg + 90)
                    if -35.0 <= slant <= 35.0:
                        angles.append(slant)

        if len(angles) >= 5:
            return float(np.median(angles))
        return 0.0

    def _estimate_stroke_thickness(self, binary_mask: np.ndarray) -> float:
        """Estimate stroke thickness via Distance Transform."""
        dist = cv2.distanceTransform(binary_mask, cv2.DIST_L2, 3)
        # Skeletonize or take the top 20% distance values on ink pixels
        ink_distances = dist[binary_mask > 0]
        if len(ink_distances) > 0:
            median_radius = np.median(ink_distances)
            # Diameter = 2 * radius
            return float(median_radius * 2.0)
        return 2.0

    def _estimate_baseline_and_line_spacing(self, binary_mask: np.ndarray) -> Tuple[float, float]:
        """Estimate line spacing and baseline jitter variance from horizontal projections."""
        h, w = binary_mask.shape
        proj = np.sum(binary_mask, axis=1) / 255.0

        # Find line peaks using smooth projection
        kernel_size = max(5, int(h * 0.01))
        if kernel_size % 2 == 0:
            kernel_size += 1
        smoothed = cv2.GaussianBlur(proj.reshape(-1, 1), (1, kernel_size), 0).flatten()

        peaks = []
        thresh_val = np.mean(smoothed) * 0.5
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] > thresh_val and smoothed[i] >= smoothed[i - 1] and smoothed[i] >= smoothed[i + 1]:
                peaks.append(i)

        # Line spacing
        if len(peaks) >= 2:
            diffs = np.diff(peaks)
            valid_diffs = [d for d in diffs if 20 < d < 120]
            line_spacing = float(np.median(valid_diffs)) if valid_diffs else 44.0
        else:
            line_spacing = 44.0

        # Baseline variance: analyze bottom y-coordinates of contours per line
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bottoms = []
        for cnt in contours:
            _, y, _, ch = cv2.boundingRect(cnt)
            if ch > 10:
                bottoms.append(y + ch)

        if len(bottoms) > 10:
            # Baseline variation can be approximated by local variance
            bottoms = np.array(bottoms)
            local_vars = []
            for b in bottoms:
                close = bottoms[np.abs(bottoms - b) < 20]
                if len(close) > 2:
                    local_vars.append(np.std(close))
            baseline_var = float(np.median(local_vars)) if local_vars else 1.5
        else:
            baseline_var = 1.5

        return line_spacing, baseline_var

    def _estimate_spacing(self, binary_mask: np.ndarray) -> Tuple[float, float]:
        """Estimate character and word spacing from contour bounding box gaps."""
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 5 and h > 10:
                boxes.append((x, y, w, h))

        if len(boxes) < 4:
            return 2.0, 20.0

        # Sort horizontally
        boxes = sorted(boxes, key=lambda b: (b[1] // 30, b[0]))
        gaps = []
        for i in range(len(boxes) - 1):
            curr_b = boxes[i]
            next_b = boxes[i + 1]
            # Same approximate line
            if abs(curr_b[1] - next_b[1]) < 25:
                gap = next_b[0] - (curr_b[0] + curr_b[2])
                if 0 < gap < 100:
                    gaps.append(gap)

        if gaps:
            gaps = np.array(gaps)
            # Smaller gaps are inter-character, larger gaps are inter-word
            char_gap = float(np.percentile(gaps, 25))
            word_gap = float(np.percentile(gaps, 75))
            return char_gap, word_gap

        return 2.0, 20.0

    def _extract_dominant_ink_color(self, img_rgb: np.ndarray, binary_mask: np.ndarray) -> Tuple[int, int, int]:
        """Extract median RGB color of ink pixels."""
        ink_pixels = img_rgb[binary_mask > 0]
        if len(ink_pixels) == 0:
            return (26, 62, 138)

        # Filter out overly bright pixels that might be paper bleed
        brightness = np.mean(ink_pixels, axis=1)
        dark_pixels = ink_pixels[brightness < 180]

        if len(dark_pixels) > 50:
            median_color = np.median(dark_pixels, axis=0).astype(int)
            return (int(median_color[0]), int(median_color[1]), int(median_color[2]))

        median_color = np.median(ink_pixels, axis=0).astype(int)
        return (int(median_color[0]), int(median_color[1]), int(median_color[2]))
