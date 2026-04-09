# पायथनची इमेज वापरा
FROM python:3.9-slim

# सर्व्हरवर FFmpeg आणि इतर गरजेच्या गोष्टी इंस्टॉल करा
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# प्रोजेक्ट डिरेक्टरी सेट करा
WORKDIR /app

# लायब्ररीज इंस्टॉल करा
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# तुमचा सर्व कोड सर्व्हरवर कॉपी करा
COPY . .

# सर्व्हर सुरू करण्याची कमांड
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--timeout", "600"]