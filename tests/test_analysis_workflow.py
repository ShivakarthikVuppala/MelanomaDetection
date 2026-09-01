from io import BytesIO

import numpy as np
import cv2
from PIL import Image, ImageDraw

from src.engine.image_quality import check_image_quality
from src.engine.measurements import (
    extract_lesion_measurements,
    refine_lesion_mask,
    refine_mask_with_scale,
)
from src.engine.scale_detection import ScaleDetector


def _synthetic_image_bytes():
    image = Image.new("RGB", (300, 300), (180, 160, 140))
    ImageDraw.Draw(image).ellipse((100, 90, 210, 220), fill=(25, 15, 12), outline=(0, 0, 0), width=4)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_quality_gate_rejects_blank_image():
    result = check_image_quality(np.zeros((300, 300, 3), dtype=np.uint8))
    assert result.accepted is False
    assert result.reason


def test_quality_gate_accepts_readable_focused_image():
    image = np.asarray(Image.open(BytesIO(_synthetic_image_bytes())).convert("RGB"))
    result = check_image_quality(image)
    assert result.accepted is True


def test_measurements_are_derived_from_mask():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[25:75, 30:70] = 1
    measurements = extract_lesion_measurements(np.zeros((100, 100, 3), dtype=np.uint8), mask)
    assert measurements["area_px"] == 2000
    assert measurements["perimeter_px"] > 0
    assert measurements["diameter_px"] > 0
    assert measurements["physical_scale_available"] is False


def test_reference_component_is_excluded_from_lesion_measurement():
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[80:130, 75:125] = 1       # lesion
    mask[20:70, 20:70] = 1         # circular reference component

    lesion_mask = refine_lesion_mask(mask, excluded_bbox=(18, 18, 55, 55))
    measurements = extract_lesion_measurements(
        np.zeros((200, 200, 3), dtype=np.uint8), lesion_mask
    )
    assert measurements["area_px"] == 2500
    assert lesion_mask[40, 40] == 0


def test_valid_circular_reference_produces_verified_calibration():
    image = np.full((400, 600, 3), 220, dtype=np.uint8)
    cv2.circle(image, (100, 100), 40, (30, 30, 30), 4)
    cv2.circle(image, (100, 100), 34, (180, 180, 180), -1)
    cv2.ellipse(image, (420, 250), (35, 50), 20, 0, 360, (40, 25, 20), -1)
    lesion_mask = np.zeros((400, 600), dtype=np.uint8)
    cv2.ellipse(lesion_mask, (420, 250), (35, 50), 20, 0, 360, 1, -1)

    calibration = ScaleDetector(
        min_circle_radius=20, max_circle_radius=100
    ).detect(
        image,
        method="circle",
        known_diameter_mm=20.0,
        lesion_mask=lesion_mask,
    )

    assert calibration.detected is True
    assert calibration.calibration_valid is True
    assert calibration.reference_diameter_px > 10
    assert calibration.reference_bbox_px is not None
    assert 3.0 < calibration.pixels_per_mm < 5.5
    assert calibration.validation_reason.startswith("valid")


def test_valid_ruler_interval_produces_verified_calibration():
    image = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.line(image, (100, 350), (500, 350), (20, 20, 20), 2)
    for x in range(110, 501, 12):
        cv2.line(image, (x, 350), (x, 330 if x % 60 else 320), (20, 20, 20), 2)

    calibration = ScaleDetector().detect(
        image, method="ruler", known_diameter_mm=1.0
    )

    assert calibration.detected is True
    assert calibration.calibration_valid is True
    assert calibration.reference_length_px == 12.0
    assert calibration.reference_length_mm == 1.0
    assert calibration.pixels_per_mm == 12.0
    assert calibration.reference_bbox_px is not None
    assert calibration.tick_spacing_px == 12.0
    assert calibration.validated_tick_count >= 20


def test_auto_ruler_calibrates_metric_minor_interval_without_fixed_ppm():
    image = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.line(image, (100, 350), (500, 350), (20, 20, 20), 2)
    for x in range(110, 501, 12):
        cv2.line(image, (x, 350), (x, 320 if x % 60 == 0 else 330), (20, 20, 20), 2)

    calibration = ScaleDetector().detect(image, method="auto")

    assert calibration.detected is True
    assert calibration.calibration_valid is True
    assert calibration.reference_length_mm == 1.0
    assert calibration.pixels_per_mm == 12.0
    assert calibration.orientation == "horizontal"
    assert calibration.tick_spacing_px == 12.0
    assert len(calibration.tick_positions_px) >= 20


def test_scale_aware_cleanup_removes_connected_low_contrast_halo():
    image = np.full((240, 240, 3), 210, dtype=np.uint8)
    mask = np.zeros((240, 240), dtype=np.uint8)
    cv2.ellipse(mask, (120, 120), (60, 45), 0, 0, 360, 1, -1)
    cv2.ellipse(image, (120, 120), (60, 45), 0, 0, 360, (175, 145, 120), -1)
    cv2.ellipse(image, (120, 120), (16, 14), 0, 0, 360, (35, 25, 20), -1)

    cleaned = refine_mask_with_scale(image, mask, pixels_per_mm=20.0)
    before = cv2.boundingRect(mask)
    after = cv2.boundingRect(cleaned)

    assert after[2] < before[2]
    assert after[3] < before[3]
    assert cleaned[120, 120] == 1


def test_lesion_primary_diameter_is_maximum_feret_and_has_mm_aliases():
    mask = np.zeros((120, 140), dtype=np.uint8)
    cv2.rectangle(mask, (30, 40), (90, 70), 1, -1)

    measurements = extract_lesion_measurements(
        np.zeros((120, 140, 3), dtype=np.uint8), mask, pixels_per_mm=10.0
    )

    assert measurements["measurement_method"] == "maximum_feret_diameter"
    assert measurements["max_feret_diameter_px"] == measurements["diameter_px"]
    assert measurements["diameter_px"] > measurements["bounding_box_width_px"]
    assert measurements["lesion_diameter_mm"] == measurements["diameter_mm"]
    assert measurements["minimum_feret_diameter_px"] > 0
    assert measurements["equivalent_diameter_px"] > 0


def test_auto_does_not_promote_an_unknown_circle_to_a_reference():
    image = np.full((300, 300, 3), 220, dtype=np.uint8)
    cv2.circle(image, (150, 150), 45, (35, 25, 20), 4)
    cv2.circle(image, (150, 150), 38, (70, 45, 35), -1)

    calibration = ScaleDetector(
        min_circle_radius=20, max_circle_radius=80
    ).detect(image, method="auto")

    assert calibration.calibration_valid is False
    assert calibration.detected is False
    assert calibration.pixels_per_mm is None


def test_lesion_mistaken_for_reference_is_rejected():
    image = np.full((400, 600, 3), 220, dtype=np.uint8)
    cv2.ellipse(image, (300, 200), (45, 45), 0, 0, 360, (30, 20, 20), 4)
    cv2.ellipse(image, (300, 200), (40, 40), 0, 0, 360, (40, 25, 20), -1)
    lesion_mask = np.zeros((400, 600), dtype=np.uint8)
    cv2.ellipse(lesion_mask, (300, 200), (40, 40), 0, 0, 360, 1, -1)

    calibration = ScaleDetector(
        min_circle_radius=20, max_circle_radius=100
    ).detect(
        image,
        method="circle",
        known_diameter_mm=20.0,
        lesion_mask=lesion_mask,
    )

    assert calibration.calibration_valid is False
    assert calibration.pixels_per_mm is None


def test_partial_or_too_small_manual_reference_is_unavailable():
    calibration = ScaleDetector().detect(
        np.zeros((100, 100, 3), dtype=np.uint8),
        method="manual",
        known_object_px=5.2,
        known_object_mm=1.0,
    )
    assert calibration.detected is True
    assert calibration.calibration_valid is False
    assert calibration.validation_reason


def test_full_frame_segmentation_is_rejected_before_measurement():
    with np.testing.assert_raises(ValueError):
        refine_lesion_mask(np.ones((100, 100), dtype=np.uint8))


def test_vignetted_segmentation_recovery_returns_bounded_interior_mask():
    from src.segmentation.segformer_wrapper import SegFormerSegmenter

    image = np.asarray(Image.open(
        r"C:\Users\shiva\Downloads\ISIC_0024644_MEL.jpg"
    ).convert("RGB"))
    full_field = np.ones(image.shape[:2], dtype=np.uint8)

    assert SegFormerSegmenter._is_dominant_border_mask(full_field)
    recovered = SegFormerSegmenter._recover_vignetted_mask(image)
    assert recovered is not None
    assert 100 < int(recovered.sum()) < int(recovered.size * 0.75)
    assert cv2.connectedComponents(recovered)[0] - 1 == 1


def test_api_rejects_unsupported_format():
    from fastapi.testclient import TestClient
    from api.server import app

    response = TestClient(app).post(
        "/api/analyze",
        files={"file": ("payload.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["detail"]["error_code"] == "unsupported_format"
    assert "Traceback" not in response.text


def test_api_returns_quality_status_without_running_models():
    from fastapi.testclient import TestClient
    import api.server as server

    blank = BytesIO()
    Image.new("RGB", (300, 300), (0, 0, 0)).save(blank, format="PNG")
    response = TestClient(server.app).post(
        "/api/analyze",
        files={"file": ("blank.png", blank.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "image_quality_insufficient"
    assert response.json()["error_code"] == "image_quality_insufficient"
    assert "Traceback" not in response.text
