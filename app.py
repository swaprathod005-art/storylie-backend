from flask import Flask, request, send_file
import subprocess
import os
import cv2
import numpy as np
import traceback

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ⚠️ FFmpeg path check
FFMPEG_PATH = r"C:\Users\taral\Downloads\ffmpeg-8.1-essentials_build (1)\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe"

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route("/", methods=["GET"])
def index():
    return "<h1>Storylie Pro Summarizer - 40 Min Target Mode</h1>"

@app.route("/summarize", methods=["POST"])
def summarize():
    print("\n--- 🔥 STARTING PRO MOVIE SUMMARIZATION (35-40 MINS) ---", flush=True)
    try:
        if 'video' not in request.files:
            return "No video file", 400

        video = request.files['video']
        video_path = os.path.join(UPLOAD_FOLDER, "input_movie.mp4")
        video.save(video_path)
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 25
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = frame_count / fps
        print(f"🎬 Original Movie: {duration_sec/60:.2f} mins", flush=True)

        # --- 🎯 DEEP ANALYSIS ---
        scores = []
        prev_gray = None
        frame_id = 0
        
        print("🎯 Finding major story points...", flush=True)
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # 1 second sampling
            if frame_id % int(fps) == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Motion (Action detection)
                motion = 0
                if prev_gray is not None:
                    motion = np.mean(cv2.absdiff(prev_gray, gray))
                
                # Characters (Face detection)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                # Weighted score
                s = (len(faces) * 200) + (motion * 20) + (np.mean(gray) * 0.1)
                scores.append({'time': frame_id / fps, 'score': s})
                prev_gray = gray
            
            frame_id += 1
        cap.release()

        # --- 📽️ SMART SCENE CLUSTERING ---
        # 2hr movie -> Need ~40 scenes of 50 seconds each to hit ~35 mins
        scene_duration = 50 
        num_scenes_to_pick = 45 
        
        # Sort by importance
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        selected_ranges = []
        for item in scores:
            if len(selected_ranges) >= num_scenes_to_pick: break
            
            t = item['time']
            # Check if this new scene overlaps with already selected ones (at least 2 min gap)
            if all(abs(t - (s+e)/2) > 120 for s, e in selected_ranges):
                start = max(0, t - 10) # Start 10s before peak
                end = min(duration_sec, start + scene_duration) # End 50s later
                selected_ranges.append((start, end))

        # Sort by timeline to keep movie sequence
        selected_ranges.sort()
        print(f"✅ Selected {len(selected_ranges)} full scenes. Estimated length: {(len(selected_ranges)*scene_duration)/60:.2f} mins", flush=True)

        # --- ✂️ HIGH-QUALITY JOINING ---
        list_file = os.path.join(OUTPUT_FOLDER, "concat_list.txt")
        with open(list_file, "w") as f:
            for i, (s, e) in enumerate(selected_ranges):
                clip_path = os.path.join(OUTPUT_FOLDER, f"scene_{i}.mp4")
                dur = e - s
                
                # Cut command with high-quality settings
                cmd = [
                    FFMPEG_PATH, "-y", "-ss", str(s), "-i", video_path, 
                    "-t", str(dur), "-c:v", "libx264", "-preset", "ultrafast", 
                    "-pix_fmt", "yuv420p", "-c:a", "aac", clip_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if os.path.exists(clip_path):
                    f.write(f"file '{os.path.abspath(clip_path)}'\n")

        final_summary = os.path.join(OUTPUT_FOLDER, "movie_summary.mp4")
        
        # Merge scenes
        merge_cmd = [
            FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", list_file, 
            "-c", "copy", "-movflags", "+faststart", final_summary
        ]
        
        print("🔗 Merging into final 35-40 min movie...", flush=True)
        subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"🚀 DONE! Final Summary Size: {os.path.getsize(final_summary)/(1024*1024):.2f} MB", flush=True)
        return send_file(os.path.abspath(final_summary), as_attachment=True)

    except Exception as e:
        print(f"❌ SERVER ERROR:\n{traceback.format_exc()}")
        return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)