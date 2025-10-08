from flask import Flask, request, jsonify, send_from_directory
import subprocess, tempfile, os, socket, time, threading

app = Flask(__name__, static_folder='noVNC')

sessions = {}

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_gui(code):
    pyfile = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    pyfile.write(code.encode())
    pyfile.close()

    display_num = get_free_port()
    port = get_free_port()

    subprocess.Popen(["Xvfb", f":{display_num}", "-screen", "0", "1024x768x24"])
    time.sleep(1)

    env = os.environ.copy()
    env["DISPLAY"] = f":{display_num}"

    python_proc = subprocess.Popen(["python3", pyfile.name], env=env)

    x11vnc_proc = subprocess.Popen([
        "x11vnc",
        "-display", f":{display_num}",
        "-nopw", "-forever", "-shared",
        "-rfbport", str(port)
    ])

    ws_port = get_free_port()
    ws_proc = subprocess.Popen([
        "websockify", str(ws_port), f"localhost:{port}"
    ])

    sessions[ws_port] = (python_proc, x11vnc_proc, ws_proc, pyfile.name)

    def cleanup():
        time.sleep(300)
        python_proc.kill()
        x11vnc_proc.kill()
        ws_proc.kill()
        os.remove(pyfile.name)
        del sessions[ws_port]

    threading.Thread(target=cleanup).start()

    return ws_port

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    code = data.get("code", "")
    time.sleep(5)
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
    