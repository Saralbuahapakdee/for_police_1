from flask import Flask, Response
from PIL import Image, ImageDraw
import io, time, datetime

app = Flask(__name__)

def generate():
    while True:
        img = Image.new("RGB", (640, 360), (30, 30, 30))
        d = ImageDraw.Draw(img)
        d.text((20, 20), datetime.datetime.now().strftime("%H:%M:%S"), fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        frame = buf.getvalue()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.5)

@app.get("/stream")
def stream():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
