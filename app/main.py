import os
import subprocess
from flask import Flask, Response, jsonify

from napster import bp as napster_bp
from rehearsal import bp as rehearsal_bp
from ui import PAGE

app = Flask(__name__)
app.register_blueprint(rehearsal_bp)
app.register_blueprint(napster_bp)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
