from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
from PIL import Image
import numpy as np
import torch

class SegmentationPredictor:
    def __init__(self):
        model_name = "nvidia/segformer-b0-finetuned-ade-512-512"

        self.processor = SegformerImageProcessor.from_pretrained(model_name)
        self.model = SegformerForSemanticSegmentation.from_pretrained(model_name)
        self.model.eval()

        self.labels = self.model.config.id2label

    def predict(self, image: Image.Image) -> dict:
        inputs = self.processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        predicted = logits.argmax(dim=1)[0]

        unique, counts = torch.unique(predicted, return_counts=True)
        total_pixels = predicted.numel()

        segments = []
        for class_id, count in zip(unique.tolist(), counts.tolist()):
            score = round(count / total_pixels, 3)
            if score > 0.01:
                segments.append({
                    "label": self.labels[class_id],
                    "score": score
                })

        segments.sort(key=lambda x: x["score"], reverse=True)

        return {"segments": segments, "total": len(segments)}

    def predict_with_overlay(self, image: Image.Image) -> Image.Image:
        inputs = self.processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        upsampled = torch.nn.functional.interpolate(
            logits,
            size=image.size[::-1],
            mode="bilinear",
            align_corners=False
        )
        predicted = upsampled.argmax(dim=1)[0].numpy()



        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 0), (0, 128, 0), (0, 0, 128),
            (255, 128, 0), (128, 0, 255), (0, 128, 255),
        ]

        img_array = np.array(image.convert("RGB")).astype(np.float32)
        overlay = img_array.copy()

        for class_id in np.unique(predicted):
            color = colors[class_id % len(colors)]
            mask = predicted == class_id
            for c, val in enumerate(color):
                overlay[:, :, c] = np.where(
                    mask,
                    img_array[:, :, c] * 0.5 + val * 0.5,
                    overlay[:, :, c]
                )

        return Image.fromarray(overlay.astype(np.uint8))


predictor = SegmentationPredictor()