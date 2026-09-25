"""Syntax-check every piece of JavaScript the dashboard serves (needs `node`): the .js files and the inline <script> blocks
of the HTML pages. A single typo there silently breaks a whole page, and nothing else in the tests would notice.
    python tests/check_frontend.py"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DASH = Path(__file__).parent.parent / "dashboard"
bad, checked = [], 0


def check(name: str, code: str):
    global checked
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(code)
    r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
    checked += 1
    if r.returncode:
        bad.append(f"{name}: {r.stderr.strip().splitlines()[0:3]}")


for js in sorted(DASH.glob("*.js")):
    check(js.name, js.read_text())
for html in sorted(DASH.glob("*.html")):
    for i, m in enumerate(re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html.read_text(), re.S)):
        check(f"{html.name} inline script {i + 1}", m.group(1))
print(f"checked {checked} scripts")
if bad:
    sys.exit("JavaScript syntax errors:\n" + "\n".join(bad))
