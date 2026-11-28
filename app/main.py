import os
import subprocess
from flask import Flask, Response, jsonify

from napster import bp as napster_bp
from rehearsal import bp as rehearsal_bp
from core import bp as core_bp
from consent import bp as consent_bp
from coach import bp as coach_bp
from ui import PAGE

app = Flask(__name__)
app.register_blueprint(rehearsal_bp)
app.register_blueprint(core_bp)
app.register_blueprint(napster_bp)
app.register_blueprint(consent_bp)
app.register_blueprint(coach_bp)

# Vendored, unmodified Napster Web SDK 2.0.0 (SHA-256 pinned in app/ui.py and
# app/vendor/napster-companion-api/2.0.0/PROVENANCE.md). Served same-origin only
# after the user explicitly opts in; nothing is fetched on page load.
SDK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "vendor", "napster-companion-api", "2.0.0",
)

def get_git_sha():
    """Get the current git commit SHA, with fallback to 'unknown'"""
    try:
        # Try to get the BUILD_SHA environment variable first
        build_sha = os.environ.get('BUILD_SHA')
        if build_sha:
            return build_sha

        # Try to get the current git commit SHA
        result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        # Fallback to unknown if we can't determine the SHA
        return 'unknown'

@app.route('/health')
def health():
    # Get the current commit SHA
    sha = get_git_sha()
    return jsonify({"status": "ok", "version": sha})

@app.route('/')
def index():
    return Response(PAGE, mimetype='text/html')

@app.route('/vendor/napster-companion-api/2.0.0/bundle.js')
def napster_sdk_bundle():
    with open(os.path.join(SDK_DIR, 'bundle.js'), 'rb') as fh:
        data = fh.read()
    return Response(data, mimetype='text/javascript')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
