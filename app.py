from flask import Flask, request, jsonify, send_from_directory
import subprocess, tempfile, os, socket, time, threading, sys, re

app = Flask(__name__, static_folder='noVNC')
sessions = {}

# Fixed ports for Render
RFB_PORT = 6080
WS_PORT = 6081

def get_required_libs(code):
    libs = re.findall(r"^\s*import (\w+)|from (\w+) import", code, re.MULTILINE)
    return [lib for lib in libs if lib in ["PySide6","PyQt6","kivy","flet"]]

def install_lib(lib):
    subprocess.run([sys.executable, "-m", "pip", "install", lib], check=False)

def run_gui(code):
    pyfile = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    pyfile.write(code.encode())
    pyfile.close()

    # Auto install missing libraries
    for lib in get_required_libs(code):
        try:
            __import__(lib)
        except ModuleNotFoundError:
            install_lib(lib)

    # Start Xvfb
    display_num = 99
    env = os.environ.copy()
    env["DISPLAY"] = f":{display_num}"
    subprocess.Popen(["Xvfb", f":{display_num}", "-screen", "0", "1024x768x24"], env=env)
    time.sleep(1)

    python_proc = subprocess.Popen([sys.executable, pyfile.name], env=env)
    x11vnc_proc = subprocess.Popen(["x11vnc", "-display", f":{display_num}", "-nopw", "-forever", "-shared", "-rfbport", str(RFB_PORT)])
    ws_proc = subprocess.Popen(["websockify", str(WS_PORT), f"localhost:{RFB_PORT}"])

    sessions[WS_PORT] = (python_proc, x11vnc_proc, ws_proc, pyfile.name)

    def cleanup():
        time.sleep(300)
        python_proc.kill()
        x11vnc_proc.kill()
        ws_proc.kill()
        os.remove(pyfile.name)
        del sessions[WS_PORT]

    threading.Thread(target=cleanup).start()
    return WS_PORT

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    code = data.get("code", "")
    ws_port = run_gui(code)
    return jsonify({"vnc_port": ws_port})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/noVNC/<path:path>')
def serve_novnc(path):
    return send_from_directory('noVNC', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    