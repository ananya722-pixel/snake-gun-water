import re
import shutil
import subprocess
import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

BASE_DIR = Path(__file__).parent
app = Flask(__name__, static_folder="static")


def python_command():
    # On some hosts (e.g. uWSGI) sys.executable is not the python program,
    # so fall back to python3 / python when it doesn't look like python.
    if "python" in Path(sys.executable).name.lower():
        return sys.executable
    return shutil.which("python3") or shutil.which("python") or "python3"


@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@app.route("/play", methods=["POST"])
def play():
    data = request.get_json(silent=True) or {}
    choice = data.get("choice")

    # main.py crashes on anything except s / w / g, so check here first
    if choice not in ("s", "w", "g"):
        return jsonify({"error": "choice must be 's', 'w' or 'g'"}), 400

    # Run your main.py, type the choice into it, and capture what it prints
    proc = subprocess.run(
        [python_command(), str(BASE_DIR / "main.py")],
        input=choice + "\n",
        capture_output=True,
        text=True,
        timeout=5,
    )
    output = proc.stdout.lower()

    you = re.search(r"you chose\s*(\w+)", output)
    computer = re.search(r"computer chose\s*(\w+)", output)

    if proc.returncode != 0 or not you or not computer:
        return jsonify({"error": "main.py failed", "details": proc.stderr}), 500

    if "draw" in output:
        result = "draw"
    elif "lose" in output:
        result = "lose"
    elif "won" in output or "win" in output:
        result = "win"
    else:
        return jsonify({"error": "could not read the result from main.py"}), 500

    return jsonify({
        "you": you.group(1),
        "computer": computer.group(1),
        "result": result,
    })


if __name__ == "__main__":
    app.run(debug=True)