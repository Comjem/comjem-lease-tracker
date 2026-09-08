from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json, os, datetime
import urllib.parse as urlparse

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
BASE = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:C5+7Z7kTVqsbWSh@db.eazplxtbrsmhnluinqta.supabase.co:5432/postgres')

import pg8000.native

def get_conn():
    url = urlparse.urlparse(DATABASE_URL)
    return pg8000.native.Connection(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port or 5432,
        database=url.path[1:],
        ssl_context=True
    )

def init_db():
    conn = get_conn()
    conn.run('''CREATE TABLE IF NOT EXISTS leases (
        id TEXT PRIMARY KEY, tenant TEXT, address TEXT, building TEXT,
        expiration TEXT, exp_sort TEXT, source TEXT, notes TEXT, updated_at TEXT
    )''')
    count = conn.run('SELECT COUNT(*) FROM leases')[0][0]
    if count == 0:
        seed_path = os.path.join(BASE, 'seed.json')
        if os.path.exists(seed_path):
            with open(seed_path, encoding='utf-8') as f:
                seed = json.load(f)
            now = datetime.datetime.utcnow().isoformat()
            for l in seed:
                conn.run(
                    'INSERT INTO leases (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at) VALUES (:id,:tenant,:address,:building,:expiration,:exp_sort,:source,:notes,:now) ON CONFLICT (id) DO NOTHING',
                    id=l.get('id',''), tenant=l.get('tenant',''), address=l.get('address',''),
                    building=l.get('building',''), expiration=l.get('expiration',''),
                    exp_sort=l.get('exp_sort',''), source=l.get('source',''),
                    notes=l.get('notes',''), now=now)
    conn.close()

try:
    init_db()
except Exception as e:
    print('DB init error:', e)

COLS = ['id','tenant','address','building','expiration','exp_sort','source','notes','updated_at']

def rows_to_dicts(rows):
    return [dict(zip(COLS, r)) for r in rows]

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def index():
    with open(os.path.join(BASE, 'static', 'index.html'), encoding='utf-8') as f:
        return Response(f.read(), mimetype='text/html')

@app.route('/api/leases', methods=['GET','OPTIONS'])
def get_leases():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    conn = get_conn()
    rows = conn.run('SELECT id,tenant,address,building,expiration,exp_sort,source,notes,updated_at FROM leases ORDER BY exp_sort')
    conn.close()
    return jsonify(rows_to_dicts(rows))

@app.route('/api/leases', methods=['POST'])
def add_lease():
    d = request.json; now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    conn.run(
        'INSERT INTO leases (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at) VALUES (:id,:tenant,:address,:building,:expiration,:exp_sort,:source,:notes,:now) ON CONFLICT (id) DO UPDATE SET tenant=EXCLUDED.tenant,address=EXCLUDED.address,building=EXCLUDED.building,expiration=EXCLUDED.expiration,exp_sort=EXCLUDED.exp_sort,source=EXCLUDED.source,notes=EXCLUDED.notes,updated_at=EXCLUDED.updated_at',
        id=d.get('id'), tenant=d.get('tenant'), address=d.get('address'), building=d.get('building'),
        expiration=d.get('expiration'), exp_sort=d.get('exp_sort'), source=d.get('source'),
        notes=d.get('notes'), now=now)
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['PUT','OPTIONS'])
def update_lease(lid):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    d = request.json; now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    conn.run(
        'UPDATE leases SET tenant=:tenant,address=:address,building=:building,expiration=:expiration,exp_sort=:exp_sort,source=:source,notes=:notes,updated_at=:now WHERE id=:lid',
        tenant=d.get('tenant'), address=d.get('address'), building=d.get('building'),
        expiration=d.get('expiration'), exp_sort=d.get('exp_sort'), source=d.get('source'),
        notes=d.get('notes'), now=now, lid=lid)
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['DELETE','OPTIONS'])
def delete_lease(lid):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    conn = get_conn()
    conn.run('DELETE FROM leases WHERE id=:lid', lid=lid)
    conn.close()
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
