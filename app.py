from flask import Flask, request, send_file
import subprocess
import os
import cv2
import numpy as np
import traceback

app = Flask(__name__)

# फोल्डर सेटअप (स्थानिक आणि क्लाउड दोन्हीसाठी चालेल)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# क्लाउडवर फक्त 'ffmpeg' लागते, स्थानिक (Local) साठी तुमचा पूर्ण पाथ वापरावा लागेल
# जर तुम्ही हा कोड लॅपटॉपवर रन करत असाल तर तुमचा जुना पाथ खाली वापरा
FFMPEG_PATH = "ffmpeg" 

# फेस डिटेक्शनसाठी
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route("/", methods=["GET"])
def index():
    return "<h1>Storylie AI Online</h1>"

@app.route("/summarize", methods=["POST"])
def summarize():
    print("\n--- 🔥 REQUEST RECEIVED ---", flush=True)
    try:
        if 'video' not in request.files:
            return "No video file found", 400

        video = request.files['video']
        video_path = os.path.join(UPLOAD_FOLDER, "input.mp4")
        video.save(video_path)
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        scores = []
        frame_id = 0
        
        print("🎯 Analyzing video...", flush=True)
        # दर ५ सेकंदाला १ फ्रेम चेक करा (Fast Processing)
        while True:
            ret, frame = cap.read()
            if not ret: break
            if frame_id % (int(fps) * 5) == 0:
                small = cv2.resize(frame, (320, 180))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                score = (len(faces) * 100) + (np.mean(gray) * 0.1)
                scores.append({'time': frame_id / fps, 'score': score})
            frame_id += 1
        cap.release()

        # महत्त्वाचे सीन्स निवडा
        scores.sort(key=lambda x: x['score'], reverse=True)
        selected_times = []
        for item in scores:
            if len(selected_times) >= 20: break
            t = item['time']
            if not selected_times or all(abs(t - pt) > 180 for pt in selected_times):
                selected_times.append(t)
        
        selected_times.sort()
        list_path = os.path.join(OUTPUT_FOLDER, "list.txt")
        with open(list_path, "w") as f:
            for i, t in enumerate(selected_times):
                out = os.path.join(OUTPUT_FOLDER, f"c_{i}.mp4")
                # ४० सेकंदाचा सीन कट करा
                cmd = [FFMPEG_PATH, "-y", "-ss", str(max(0, t-5)), "-i", video_path, "-t", "40", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", out]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(out): 
                    f.write(f"file '{os.path.abspath(out)}'\n")

        final = os.path.join(OUTPUT_FOLDER, "summary.mp4")
        merge_cmd = [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", "-movflags", "+faststart", final]
        subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("🚀 Success! Sending summary back.", flush=True)
        return send_file(os.path.abspath(final), as_attachment=True)

    except Exception as e:
        print(f"❌ Error: {traceback.format_exc()}", flush=True)
        return str(traceback.format_exc()), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)