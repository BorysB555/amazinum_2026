# model/predictor.py
from transformers import pipeline
from PIL import Image
import numpy as np

class SegmentationPredictor:
    def __init__(self):
        # pipeline — це та сама функція що в лекції,
        # просто інша задача: image-segmentation замість image-classification
        # device=-1 означає CPU (як в лекції)
        self.pipe = pipeline(
            "image-segmentation",
            model="nvidia/segformer-b0-finetuned-ade-512-512",
            device=-1
        )

    def predict(self, image: Image.Image) -> dict:
        """
        Приймає PIL Image, повертає словник з результатами.
        Кожен елемент results — це один знайдений об'єкт з:
          - 'label'  : назва класу (наприклад 'sky', 'car')
          - 'score'  : впевненість моделі (0.0 — 1.0)
          - 'mask'   : бінарна маска (PIL Image, чорно-біла)
        """
        results = self.pipe(image)

        output = []
        for item in results:
            output.append({
                "label": item["label"],
                "score": round(item["score"], 3),
            })

        return {
            "segments": output,
            "total": len(output)
        }

    def predict_with_overlay(self, image: Image.Image) -> Image.Image:
        """
        Повертає зображення з накладеними кольоровими масками —
        зручно для Gradio щоб показати результат візуально.
        """
        results = self.pipe(image)

        img_array = np.array(image.convert("RGB"))

        # Кольори для різних класів (BGR)
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 0), (0, 128, 0), (0, 0, 128),
        ]

        for i, item in enumerate(results):
            color = colors[i % len(colors)]
            mask_array = np.array(item["mask"]) 

            # Там де маска = True — фарбуємо з прозорістю 40%
            where_mask = mask_array > 128
            for c, val in enumerate(color):
                img_array[:, :, c] = np.where(
                    where_mask,
                    img_array[:, :, c] * 0.6 + val * 0.4,
                    img_array[:, :, c]
                ).astype(np.uint8)

        return Image.fromarray(img_array)


predictor = SegmentationPredictor()