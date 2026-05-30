"""
DriveLegal.ai - Flask Application
Main server for the Indian traffic law assistant.
IIT Madras Road Safety Hackathon 2026
"""

import os, json, sqlite3, datetime
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from dotenv import load_dotenv
import jwt
import bcrypt

# Load environment variables
load_dotenv()

# Initialize core modules
from rules_database import RulesDatabase
from challan_calculator import ChallanCalculator
from nlp_engine import NLPEngine

# App initialization
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Initialize engines
db = RulesDatabase()
calc = ChallanCalculator(db)
nlp = NLPEngine(db)

# --- Database Setup ---
DATABASE = 'drivelegal.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                safety_score INTEGER DEFAULT 100
            )
        ''')
        # Chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Community hazards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_hazards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                description TEXT,
                upvotes INTEGER DEFAULT 0,
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Calculator history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calculator_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                country TEXT NOT NULL,
                state TEXT,
                vehicle_type TEXT,
                violations TEXT NOT NULL,
                grand_total REAL NOT NULL,
                currency TEXT DEFAULT 'Rs.',
                is_repeat INTEGER DEFAULT 0,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit()

# Initialize DB on startup (safe to call repeatedly due to IF NOT EXISTS)
init_db()


# --- Authentication Middleware ---
def token_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except Exception as e:
            return jsonify({'error': 'Token is invalid'}), 401
            
        return f(current_user_id, *args, **kwargs)
    return decorated


# --- Static Routes ---
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/data/<path:filename>')
def serve_data(filename):
    """Serve JSON data files for offline caching and translations."""
    return send_from_directory('data', filename)


# --- Auth Endpoints ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (data['email'],))
        if cursor.fetchone():
            return jsonify({'error': 'Email already registered'}), 409
            
        # Hash password
        hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute('''
            INSERT INTO users (email, password_hash, full_name, phone)
            VALUES (?, ?, ?, ?)
        ''', (data['email'], hashed.decode('utf-8'), data.get('full_name', ''), data.get('phone', '')))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'User registered successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, password_hash, full_name FROM users WHERE email = ?', (data['email'],))
        user = cursor.fetchone()
        
        if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'error': 'Invalid email or password'}), 401
            
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'full_name': user['full_name'],
                'email': data['email']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Core Endpoints ---
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'db_loaded': db.is_data_loaded(),
        'ai_ready': nlp.gemini_model is not None
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400
        
    message = data['message']
    session_id = data.get('session_id', 'default')
    country_context = data.get('country_context', None)
    
    # Process through NLP engine with country context
    response = nlp.process(message, session_id=session_id, country_context=country_context)
    
    # Log to DB if auth token provided (optional)
    if 'Authorization' in request.headers:
        try:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token_data = jwt.decode(parts[1], app.config['SECRET_KEY'], algorithms=["HS256"])
                conn = get_db()
                conn.execute('''
                    INSERT INTO chat_history (user_id, session_id, message, response)
                    VALUES (?, ?, ?, ?)
                ''', (token_data['user_id'], session_id, message, response['text']))
                conn.commit()
        except Exception:
            pass # Ignore auth errors for chat logging
            
    return jsonify(response)

@app.route('/api/calculate', methods=['POST'])
def calculate_fine():
    data = request.json
    if not data or not data.get('violations'):
        return jsonify({'error': 'Violations array is required'}), 400
        
    vehicle_type = data.get('vehicle_type', 'car')
    state = data.get('state', None)
    is_repeat = data.get('is_repeat', False)
    
    result = calc.calculate_multiple(data['violations'], vehicle_type, state, is_repeat)
    return jsonify(result)

@app.route('/api/compare', methods=['GET'])
def compare_states():
    violation_key = request.args.get('violation')
    if not violation_key:
        return jsonify({'error': 'Violation key is required'}), 400
        
    vehicle_type = request.args.get('vehicle_type', 'car')
    is_repeat = request.args.get('is_repeat', 'false').lower() == 'true'
    
    result = calc.compare_states(violation_key, vehicle_type, is_repeat)
    return jsonify(result)

@app.route('/api/violations', methods=['GET'])
def get_violations():
    country = request.args.get('country', 'india')
    if country == 'india':
        return jsonify(db.get_violation_names())
    else:
        violations = db.get_country_violations(country)
        return jsonify({k: v.get('name', k) for k, v in violations.items()})

@app.route('/api/states', methods=['GET'])
def get_states():
    return jsonify({k: db.get_state_name(k) for k in db.get_all_state_keys()})

@app.route('/api/countries', methods=['GET'])
def get_countries():
    return jsonify(db.get_all_countries())

@app.route('/api/country/<country_key>', methods=['GET'])
def get_country_info(country_key):
    data = db.get_country_data(country_key)
    if not data:
        return jsonify({'error': 'Country not found'}), 404
    return jsonify(data)


# --- Geo-fencing Endpoints ---
@app.route('/api/geo/state', methods=['GET'])
def geo_state():
    """Map a city name to its state key for geo-fenced fine lookup."""
    city = request.args.get('city', '').strip()
    if not city:
        return jsonify({'error': 'City parameter is required'}), 400
    
    state_key = db.get_state_from_city(city)
    if state_key:
        state_name = db.get_state_name(state_key)
        return jsonify({
            'city': city,
            'state_key': state_key,
            'state_name': state_name
        })
    return jsonify({'city': city, 'state_key': None, 'state_name': None, 'message': 'City not found in mapping'})

@app.route('/api/geo/detect', methods=['GET'])
def geo_detect():
    """Return the city-to-state mapping for client-side geo-fencing."""
    city_map = db.state_rules.get('city_to_state_mapping', {})
    return jsonify(city_map)

@app.route('/api/calculate/global', methods=['POST'])
def calculate_global_fine():
    data = request.json
    if not data or not data.get('violations') or not data.get('country'):
        return jsonify({'error': 'Violations array and country are required'}), 400
    
    country_key = data['country']
    violations_list = data['violations']
    country_data = db.get_country_data(country_key)
    
    if not country_data:
        return jsonify({'error': 'Country not found'}), 404
    
    results = []
    grand_total = 0
    is_repeat = data.get('is_repeat', False)
    currency = country_data.get('currency_symbol', '$')
    
    for vk in violations_list:
        violation = country_data.get('violations', {}).get(vk)
        if not violation:
            results.append({'error': f'Unknown violation: {vk}'})
            continue
        
        fine_data = violation.get('fine', {})
        if is_repeat:
            fine = fine_data.get('repeat_offense', fine_data.get('first_offense', 0))
        else:
            fine = fine_data.get('first_offense', 0)
        
        grand_total += fine
        results.append({
            'violation_key': vk,
            'violation_name': violation.get('name', vk),
            'total_fine': fine,
            'is_repeat': is_repeat,
            'additional_penalties': violation.get('additional_penalties', []),
            'safety_advice': violation.get('safety_advice', ''),
        })
    
    return jsonify({
        'violations': results,
        'count': len(results),
        'grand_total': grand_total,
        'country': country_data.get('name', country_key),
        'currency': currency,
        'is_repeat': is_repeat,
    })

@app.route('/api/hazards', methods=['GET', 'POST'])
def hazards():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        # Allow anonymous hazard reporting for hackathon demo
        user_id = 0 
        
        if 'Authorization' in request.headers:
            try:
                parts = request.headers['Authorization'].split()
                if len(parts) == 2 and parts[0] == 'Bearer':
                    token_data = jwt.decode(parts[1], app.config['SECRET_KEY'], algorithms=["HS256"])
                    user_id = token_data['user_id']
            except Exception:
                pass
                
        cursor.execute('''
            INSERT INTO community_hazards (user_id, type, lat, lng, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, data['type'], data['lat'], data['lng'], data.get('description', '')))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid})
        
    else: # GET
        cursor.execute('''
            SELECT id, type, lat, lng, description, upvotes, reported_at 
            FROM community_hazards 
            WHERE reported_at >= date('now', '-7 days')
        ''')
        hazards = [dict(row) for row in cursor.fetchall()]
        return jsonify(hazards)


# --- Rules Endpoint ---
@app.route('/api/rules/<country_key>', methods=['GET'])
def get_rules(country_key):
    """Get full traffic rules for a country."""
    if country_key == 'india':
        national = db.national_rules
        return jsonify({
            'name': 'India',
            'currency': 'INR',
            'currency_symbol': 'Rs.',
            'drive_side': 'left',
            'speed_unit': 'km/h',
            'bac_limit': '0.03% (30 mg/100 ml)',
            'legal_driving_age': 18,
            'emergency_number': '112 / 100 (Police) / 108 (Ambulance)',
            'notes': 'Governed by Motor Vehicles (Amendment) Act 2019. States may have additional rules.',
            'general_rules': national.get('general_rules', {}),
            'violations': national.get('violations', {})
        })
    else:
        data = db.get_country_data(country_key)
        if not data:
            return jsonify({'error': 'Country not found'}), 404
        return jsonify(data)


# --- Dashboard ---
@app.route('/api/user/dashboard', methods=['GET'])
@token_required
def get_dashboard(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT safety_score, full_name, email FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) as count FROM chat_history WHERE user_id = ?', (user_id,))
    chat_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM community_hazards WHERE user_id = ?', (user_id,))
    hazard_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM calculator_history WHERE user_id = ?', (user_id,))
    calc_count = cursor.fetchone()['count']
    
    return jsonify({
        'user': dict(user),
        'stats': {
            'queries': chat_count,
            'reports': hazard_count,
            'calculations': calc_count,
            'violations_scanned': 0
        }
    })

@app.route('/api/user/chat-history', methods=['GET'])
@token_required
def get_chat_history(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message, response, timestamp 
        FROM chat_history WHERE user_id = ? 
        ORDER BY timestamp DESC LIMIT 50
    ''', (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    return jsonify(rows)

@app.route('/api/user/calculator-history', methods=['GET', 'POST'])
@token_required
def calculator_history(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        cursor.execute('''
            INSERT INTO calculator_history 
            (user_id, country, state, vehicle_type, violations, grand_total, currency, is_repeat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('country', 'india'),
            data.get('state', 'national'),
            data.get('vehicle_type', 'car'),
            json.dumps(data.get('violations', [])),
            data.get('grand_total', 0),
            data.get('currency', 'Rs.'),
            1 if data.get('is_repeat') else 0
        ))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid})
    else:
        cursor.execute('''
            SELECT country, state, vehicle_type, violations, grand_total, currency, is_repeat, calculated_at
            FROM calculator_history WHERE user_id = ?
            ORDER BY calculated_at DESC LIMIT 20
        ''', (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    use_ssl = int(os.environ.get('USE_SSL', 0))
    
    print(f"\n[*] DriveLegal.ai Server starting on port {port}")
    print(f"[*] Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"[*] AI Engine: {'ONLINE' if nlp.gemini_model else 'OFFLINE FALLBACK'}")
    
    if use_ssl and os.path.exists('ssl/drivelegal.crt') and os.path.exists('ssl/drivelegal.key'):
        print(f"[*] Mode: HTTPS (SSL Enabled)")
        app.run(host='0.0.0.0', port=port, ssl_context=('ssl/drivelegal.crt', 'ssl/drivelegal.key'))
    else:
        print(f"[*] Mode: HTTP")
        app.run(host='0.0.0.0', port=port)


