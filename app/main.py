import os
import subprocess
from flask import Flask, jsonify

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)