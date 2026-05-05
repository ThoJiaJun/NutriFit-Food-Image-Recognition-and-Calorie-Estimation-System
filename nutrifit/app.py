import os
import cv2
from flask import Flask, render_template, request, redirect, url_for
from ultralytics import YOLO

app = Flask(__name__)

# -------------------------
# PATH SETUP
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
MODEL_PATH = os.path.join(BASE_DIR, "model", "yolov8n.pt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# LOAD MODEL (LOCAL ONLY)
# -------------------------
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("Model not found in /model folder!")

model = YOLO(MODEL_PATH)

# -------------------------
# FOOD FILTER LIST
# -------------------------
FOOD_CLASSES = {
    "apple", "banana", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "sandwich"
}

# -------------------------
# TEMP STORAGE
# -------------------------
latest_image = None
latest_detections = []


# -------------------------
# HOME
# -------------------------
@app.route('/')
def home():
    return render_template("upload.html")


# -------------------------
# UPLOAD + DETECT + WEIGHT
# -------------------------
@app.route('/upload', methods=['POST'])
def upload():

    global latest_image, latest_detections

    file = request.files['file']

    if file.filename == "":
        return "No file selected"

    # Save image
    image_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(image_path)

    latest_image = file.filename

    # Run YOLO
    results = model(image_path)[0]

    img = cv2.imread(image_path)

    detections = []

    SCALE_FACTOR = 0.01  # adjust later for better accuracy

    # -------------------------
    # DETECTION LOOP
    # -------------------------
    for box in results.boxes:

        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        label = model.names[cls_id]

        if label in FOOD_CLASSES:

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Draw bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Estimate weight
            area = (x2 - x1) * (y2 - y1)
            weight = int(area * SCALE_FACTOR)

            text = f"{label} {weight}g"

            cv2.putText(img, text,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2)

            detections.append({
                "food": label,
                "weight": weight
            })

    # -------------------------
    # SAVE OUTPUT IMAGE
    # -------------------------
    output_filename = "boxed_" + file.filename
    output_path = os.path.join(UPLOAD_FOLDER, output_filename)

    cv2.imwrite(output_path, img)

    latest_image = output_filename

    # -------------------------
    # REMOVE DUPLICATES
    # -------------------------
    unique = {}

    for item in detections:
        label = item["food"]

        if label not in unique or item["weight"] > unique[label]["weight"]:
            unique[label] = item

    latest_detections = list(unique.values())

    return render_template(
        "result.html",
        image_file=latest_image,
        detections=latest_detections
    )


# -------------------------
# CONTINUE PAGE
# -------------------------
@app.route('/continue')
def continue_page():
    return render_template(
        "edit.html",
        image_file=latest_image,
        detections=latest_detections
    )


# -------------------------
# TRY AGAIN
# -------------------------
@app.route('/try_again')
def try_again():
    return redirect(url_for('home'))


# -------------------------
# RUN APP
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)