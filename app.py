import os
from flask import Flask, request, render_template
from roboflow import Roboflow

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Roboflow model
rf = Roboflow(api_key="EcLMIpZXu4IRkUeokYSi")  # replace with your actual API key
project = rf.workspace("usernames-workspace").project("food-detection-epzr3-qaj9d")
model = project.version(2).model

@app.route('/')
def home():
    return render_template("Food Upload.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist("file")  # get multiple files

    if not files or all(f.filename == "" for f in files):
        return "No files selected"

    results = []  # store results for each file

    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Run inference
        prediction = model.predict(file_path, confidence=0.15).json()
        detections = []
        for item in prediction.get("predictions", []):
            detections.append({
                "label": item["class"],
                "confidence": round(item["confidence"] * 100, 2)
            })

        # Save annotated image as PNG
        annotated_filename = "prediction_" + os.path.splitext(file.filename)[0] + ".png"
        annotated_path = os.path.join(UPLOAD_FOLDER, annotated_filename)
        try:
            model.predict(file_path).save(annotated_path)
        except Exception as e:
            print("Annotated image save failed:", e)
            annotated_filename = None

        results.append({
            "annotated_file": annotated_filename,
            "detections": detections
        })

    return render_template("Food Upload.html", results=results)

if __name__ == '__main__':
    app.run(debug=True)