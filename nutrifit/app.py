import os
import cv2
import time

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
# LOAD MODEL
# -------------------------
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("Model not found in /model folder!")

model = YOLO(MODEL_PATH)

# -------------------------
# FOOD CLASSES
# -------------------------
FOOD_CLASSES = {
    "apple",
    "banana",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "sandwich"
}

# -------------------------
# SIMPLE WEIGHT MAP
# -------------------------
FOOD_WEIGHT_MAP = {
    "pizza": 250,
    "apple": 180,
    "banana": 120,
    "donut": 90,
    "cake": 200,
    "sandwich": 150,
    "orange": 130,
    "broccoli": 100,
    "carrot": 80,
    "hot dog": 160
}

# -------------------------
# TEMP STORAGE
# -------------------------
latest_image = None
latest_detections = []

# -------------------------
# HOME PAGE
# -------------------------
@app.route('/')
def home():
    return render_template("upload.html")

# -------------------------
# UPLOAD + DETECT
# -------------------------
@app.route('/upload', methods=['POST'])
def upload():

    global latest_image, latest_detections

    file = request.files['file']

    if file.filename == "":
        return "No file selected"

    # -------------------------
    # UNIQUE FILE NAME
    # -------------------------
    filename = str(int(time.time())) + "_" + file.filename

    image_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(image_path)

    # -------------------------
    # RUN YOLO
    # -------------------------
    results = model(image_path)[0]

    img = cv2.imread(image_path)

    detections = []

    # -------------------------
    # DETECTION LOOP
    # -------------------------
    for box in results.boxes:

        confidence = float(box.conf[0])

        # Ignore weak detections
        if confidence < 0.20:
            continue

        cls_id = int(box.cls[0])

        label = model.names[cls_id]

        # Ignore non-food objects
        if label not in FOOD_CLASSES:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        # -------------------------
        # DRAW BOX
        # -------------------------
        cv2.rectangle(
            img,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        # -------------------------
        # ESTIMATE WEIGHT
        # -------------------------
        weight = FOOD_WEIGHT_MAP.get(label, 100)

        # -------------------------
        # LABEL TEXT
        # -------------------------
        text = f"{label} {weight}g"

        cv2.putText(
            img,
            text,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

        detections.append({
            "food": label,
            "weight": weight
        })

    # -------------------------
    # SAVE OUTPUT IMAGE
    # -------------------------
    output_filename = "boxed_" + filename

    output_path = os.path.join(
        UPLOAD_FOLDER,
        output_filename
    )

    cv2.imwrite(output_path, img)

    latest_image = output_filename

    # -------------------------
    # GROUP SAME FOOD + COUNT
    # -------------------------
    grouped = {}

    for item in detections:

        label = item["food"]

        if label not in grouped:

            grouped[label] = {
                "food": label,
                "weight": item["weight"],
                "quantity": 1
            }

        else:
            grouped[label]["quantity"] += 1

    latest_detections = list(grouped.values())

    # -------------------------
    # SHOW RESULT PAGE
    # -------------------------
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
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True
    )
