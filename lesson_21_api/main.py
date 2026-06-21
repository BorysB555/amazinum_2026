from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import gradio as gr
from PIL import Image
import io

from model.predictor import predictor


app = FastAPI(title="Segmentation API")


@app.get("/")
def root():
    return {"status": "ok", "message": "Segmentation API is running"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):

    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    result = predictor.predict(image)

    return JSONResponse(content=result)


def gradio_predict(image):
    if image is None:
        return None, "Завантажте зображення"

    overlay = predictor.predict_with_overlay(image)

    result = predictor.predict(image)
    lines = [f"{s['label']}: {s['score']}" for s in result["segments"]]
    text = f"Знайдено {result['total']} об'єктів:\n" + "\n".join(lines)

    return overlay, text


demo = gr.Interface(
    fn=gradio_predict,
    inputs=gr.Image(type="pil", label="Завантажте зображення"),
    outputs=[
        gr.Image(type="pil", label="Результат сегментації"),
        gr.Textbox(label="Знайдені об'єкти"),
    ],
    title="Сегментація зображень",
)

app = gr.mount_gradio_app(app, demo, path="/ui")


# Запуск: uvicorn main:app --reload