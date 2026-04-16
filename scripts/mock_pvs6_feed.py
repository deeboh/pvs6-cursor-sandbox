from flask import Flask, jsonify
from datetime import datetime
app = Flask(__name__)

@app.get('/health')
def health():
    return {'ok': True, 'service': 'mock-pvs6-feed'}

@app.get('/telemetry/today')
def telemetry_today():
    return jsonify({
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'site': 'PVS6 Sandbox Site',
        'energy_kwh_today': 31.8,
        'peak_power_kw': 5.4,
        'inverter_status': 'online',
        'uptime_percent': 99.7,
        'weather_summary': 'clear morning, light clouds afternoon',
        'co2_offset_kg': 12.9,
        'dashboard_url': 'https://staging.example.com/pvs6'
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4020)
