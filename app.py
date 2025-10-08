from flask import Flask, request, jsonify, send_from_directory
import subprocess, tempfile, os, socket, time, threading, sys, uuid, ast, re

app = Flask(__name__, static_folder='noVNC')
sessions = {}

GUI_LIBS = {
    "tkinter": "tkinter",
    "customtkinter": "customtkinter",
    "PySide6": "PySide6",
    "PyQt5": "PyQt5",
    "PySimpleGUI": "PySimpleGUI",
    "kivy": "kivy",
    "flet": "flet"
}

def detect_imports(code):
    try:
        tree = ast.parse(code)
        libs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    libs.add(n.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                libs.add(node.module.split('.')[0])
        if re.search(r'App\(', code):
            libs.add("kivy")
        if re.search(r'flet\.', code, re.IGNORECASE):
            libs.add("flet")
        return libs
    except:
        return set()

def ensure_lib_installed(lib_name):
    try:
        __import__(lib_name)
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", lib_name], check=True)

def detect_and_install_libs(code):
    imports = detect_imports(code)
    detected = []
    for lib, pip_name in GUI_LIBS.items():
        if lib in imports:
            ensure_lib_installed(pip_name)
            detected.append(lib)
    return detected

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_gui(code):
    detected_libs = detect_and_install_libs(code)
    gui_name = detected_libs[0] if detected_libs else "Unknown"

    pyfile = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    pyfile.write(code.encode())
    pyfile.close()

    display_num = get_free_port() % 100
    vnc_port = get_free_port()
    ws_port = get_free_port()
    flet_port = get_free_port()

    env = os.environ.copy()

    if gui_name.lower() != "flet":
        subprocess.Popen(["Xvfb", f":{display_num}", "-screen", "0", "1024x768x24"])
        time.sleep(1)
        env["DISPLAY"] = f":{display_num}"

    # Flet: auto-run on internal port
    if gui_name.lower() == "flet":
        python_proc = subprocess.Popen([sys.executable, pyfile.name, "--port", str(flet_port)], env=env)
        ws_proc = None
        x11vnc_proc = None
        session_port = flet_port
    else:
        python_proc = subprocess.Popen([sys.executable, pyfile.name], env=env)
        x11vnc_proc = subprocess.Popen([
            "x11vnc", "-display", f":{display_num}", "-nopw", "-forever", "-shared",
            "-rfbport", str(vnc_port)
        ])
        ws_proc = subprocess.Popen([
            "websockify", str(ws_port), f"localhost:{vnc_port}"
        ])
        session_port = ws_port

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "python": python_proc,
        "x11vnc": x11vnc_proc,
        "ws": ws_proc,
        "file": pyfile.name,
        "display": display_num,
        "port": session_port,
        "gui": gui_name
    }

    def cleanup():
        time.sleep(300)
        python_proc.kill()
        if x11vnc_proc: x11vnc_proc.kill()
        if ws_proc: ws_proc.kill()
        os.remove(pyfile.name)
        del sessions[session_id]

    threading.Thread(target=cleanup).start()
    return session_id, session_port, gui_name

@app.route("/run", methods=["POST"])
def run():
    try:
        data = request.json
        code = data.get("code", "")
        session_id, port, gui_name = run_gui(code)
        return jsonify({"session_id": session_id, "port": port, "gui": gui_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions")
def get_sessions():
    return jsonify({sid: {"port": s["port"], "gui": s["gui"]} for sid, s in sessions.items()})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/noVNC/<path:path>')
def serve_novnc(path):
    return send_from_directory('noVNC', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    