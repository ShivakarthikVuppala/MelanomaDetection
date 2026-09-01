from pathlib import Path

import gradio as gr

from inference import MelanomaPredictor, format_prediction

SPACE_DIR = Path(__file__).resolve().parent
CHECKPOINT_PATH = SPACE_DIR / "best_swin_checkpoint.pth"
predictor = None
startup_error = None
if CHECKPOINT_PATH.exists():
    try:
        predictor = MelanomaPredictor(CHECKPOINT_PATH)
    except Exception as exc:
        startup_error = f"Model could not be loaded: {exc}"
else:
    startup_error = "Upload best_swin_checkpoint.pth to the Space repository before using the app."


def classify(image):
    if image is None:
        raise gr.Error("Please upload an image.")
    if predictor is None:
        raise gr.Error(startup_error)
    result = predictor.predict(image)
    return format_prediction(result), result["probabilities"]


with gr.Blocks(title="Melanoma classifier") as demo:
    gr.Markdown("# Melanoma classifier\nUpload an image to run the existing Swin V2 inference pipeline.")
    image = gr.Image(type="numpy", label="Image")
    run = gr.Button("Classify")
    prediction = gr.Textbox(label="Prediction")
    probabilities = gr.Label(label="Probabilities", num_top_classes=2)
    run.click(classify, inputs=image, outputs=[prediction, probabilities])

if __name__ == "__main__":
    demo.launch()
