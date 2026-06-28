import os
import threading
import time

# Web streaming mode flag. Set by dms_main via the --web command-line flag
# (which exports DMS_WEB=1) BEFORE this module is first imported.
WEB_MODE = os.environ.get("DMS_WEB") == "1"

# Fixed left-to-right order for the mosaic panels. Any other published frame
# is appended after these, in insertion order.
_PANEL_ORDER = ["DMS", "MONITOR AMBIENTALE", "ALCOL ALERT"]
_PANEL_HEIGHT = 360

_frames = {}
_lock = threading.Lock()
_server_started = False

_INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DMS Live View</title>
  <style>
    body { background:#121212; color:#eee; font-family:Arial, sans-serif;
           text-align:center; margin:0; padding:12px; }
    h2 { margin:8px 0; }
    img { max-width:100%; height:auto; border:2px solid #333; border-radius:8px; }
  </style>
</head>
<body>
  <h2>Driver Monitoring System - Live View</h2>
  <img src="/stream">
</body>
</html>"""


def update_frame(name, frame):
    """Publish the latest frame for a named panel to the web stream."""
    with _lock:
        _frames[name] = frame


def clear_frame(name):
    """Remove a panel from the web stream (e.g. when an alert closes)."""
    with _lock:
        _frames.pop(name, None)


def _label_panel(img, text):
    import cv2
    import numpy as np
    bar = np.full((28, img.shape[1], 3), 40, dtype=np.uint8)
    cv2.putText(bar, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return np.vstack([bar, img])


def _build_mosaic():
    import cv2
    import numpy as np
    with _lock:
        snapshot = dict(_frames)

    if not snapshot:
        placeholder = np.full((_PANEL_HEIGHT, 640, 3), 30, dtype=np.uint8)
        cv2.putText(placeholder, "Waiting for sensor frames...",
                    (30, _PANEL_HEIGHT // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (200, 200, 200), 2)
        return placeholder

    names = [n for n in _PANEL_ORDER if n in snapshot]
    names += [n for n in snapshot if n not in _PANEL_ORDER]

    tiles = []
    for name in names:
        frame = snapshot[name]
        h, w = frame.shape[:2]
        scale = _PANEL_HEIGHT / float(h)
        resized = cv2.resize(frame, (max(1, int(w * scale)), _PANEL_HEIGHT))
        tiles.append(_label_panel(resized, name))

    return cv2.hconcat(tiles)


def _mjpeg_generator():
    import cv2
    while True:
        mosaic = _build_mosaic()
        ok, buffer = cv2.imencode(".jpg", mosaic)
        if ok:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
        time.sleep(0.05)


def _detect_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def start_server(port=8000):
    """Start the MJPEG web server in a background daemon thread.

    Returns the access URL (e.g. http://192.168.1.5:8000), or None if the
    server was already started.
    """
    global _server_started
    if _server_started:
        return None

    import logging
    from flask import Flask, Response, render_template_string

    app = Flask(__name__)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    @app.route("/")
    def _index():
        return render_template_string(_INDEX_HTML)

    @app.route("/stream")
    def _stream():
        return Response(_mjpeg_generator(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    def _run():
        app.run(host="0.0.0.0", port=port, debug=False,
                use_reloader=False, threaded=True)

    threading.Thread(target=_run, daemon=True).start()
    _server_started = True
    return f"http://{_detect_ip()}:{port}"
