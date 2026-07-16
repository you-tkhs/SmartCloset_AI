"""design.md 8.2節: yolo_service.segment_item()。

移植元: ai_prototype/pipe-line/smartcloset_pipeline_functioned.ipynb の
segment_item()。ロジックは変更禁止(モデルを引数で受け取り、dataclassで返す点のみ変更)。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class SegmentResult:
    rgba: np.ndarray | None  # 背景透過RGBA画像。失敗時None
    mask: np.ndarray | None  # 0-255マスク。失敗時None
    yolo_result: Any | None  # ultralyticsのResult。annotated生成に使用
    info: dict | None  # pred_class / confidence / num_instances / all_pred_classes / all_confidences
    status: str  # "success" | "image_read_error" | "no_mask"


def segment_item(model: YOLO, image_path: Path, conf: float) -> SegmentResult:
    image_path = Path(image_path)

    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        return SegmentResult(rgba=None, mask=None, yolo_result=None, info=None, status="image_read_error")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    results = model.predict(
        source=str(image_path),
        conf=conf,
        save=False,
        verbose=False,
    )

    result = results[0]

    if result.masks is None or len(result.masks.data) == 0:
        return SegmentResult(rgba=None, mask=None, yolo_result=result, info=None, status="no_mask")

    masks = result.masks.data.cpu().numpy()
    boxes = result.boxes

    confs = boxes.conf.cpu().numpy()
    cls_ids = boxes.cls.cpu().numpy().astype(int)

    best_idx = int(np.argmax(confs))
    pred_class_id = int(cls_ids[best_idx])
    pred_class = model.names[pred_class_id]
    confidence = float(confs[best_idx])

    target_indices = np.where(cls_ids == pred_class_id)[0]

    combined_mask = np.zeros_like(masks[0], dtype=np.float32)
    for idx in target_indices:
        combined_mask = np.maximum(combined_mask, masks[idx])

    mask = (combined_mask * 255).astype(np.uint8)
    mask = cv2.resize(mask, (img_rgb.shape[1], img_rgb.shape[0]))

    rgba = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2RGBA)
    rgba[:, :, 3] = mask

    info = {
        "pred_class": pred_class,
        "confidence": confidence,
        "num_instances": int(len(target_indices)),
        "all_pred_classes": [model.names[int(c)] for c in cls_ids],
        "all_confidences": [float(c) for c in confs],
    }

    return SegmentResult(rgba=rgba, mask=mask, yolo_result=result, info=info, status="success")
