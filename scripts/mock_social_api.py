from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path
import json, os, uuid

app = Flask(__name__)
LOG_DIR = Path(os.getenv('LOG_DIR', './logs'))
LOG_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS = LOG_DIR / 'social_drafts.jsonl'

@app.get('/health')
def health():
    return {'ok': True, 'service': 'mock-social-api'}

@app.post('/draft')
def create_draft():
    payload = request.get_json(force=True)
    record = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'mode': 'draft-only',
        'payload': payload
    }
    with DRAFTS.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')
    return jsonify({'status': 'draft_saved', 'id': int(datetime.utcnow().timestamp())})

@app.post('/publish')
def publish_blocked():
    return jsonify({'status': 'blocked', 'reason': 'sandbox mode prevents live publishing'}), 403

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4010)