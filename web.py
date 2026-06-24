import os
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify

import sys
# Ensure the root folder is in path so we can import the CLI modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

import loader
import engine
import classifier
import ai_reason
import config

app = Flask(__name__, static_folder='web_static')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

@app.route('/api/events', methods=['POST'])
def get_events():
    if 'events_csv' not in request.files:
        return jsonify({"error": "Missing events_csv"}), 400
        
    events_file = request.files['events_csv']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
        events_file.save(tmp.name)
        tmp_path = Path(tmp.name)
        
    try:
        multipliers = loader.load_event_multipliers(tmp_path)
        events = list(multipliers.keys())
        return jsonify({"events": events})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        os.unlink(tmp_path)

@app.route('/api/validate_inventory', methods=['POST'])
def validate_inventory():
    if 'inventory_csv' not in request.files:
        return jsonify({"error": "Missing inventory_csv"}), 400
        
    inv_file = request.files['inventory_csv']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
        inv_file.save(tmp.name)
        tmp_path = Path(tmp.name)
        
    try:
        loader.load_inventory_sales(tmp_path)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        os.unlink(tmp_path)

@app.route('/api/process', methods=['POST'])
def process():
    if 'inventory_csv' not in request.files or 'events_csv' not in request.files:
        return jsonify({"error": "Missing CSV files"}), 400
        
    event_name = request.form.get('event_name')
    use_ai = request.form.get('use_ai') == 'true'
    
    inv_file = request.files['inventory_csv']
    evt_file = request.files['events_csv']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_inv, \
         tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_evt:
        inv_file.save(tmp_inv.name)
        evt_file.save(tmp_evt.name)
        inv_path = Path(tmp_inv.name)
        evt_path = Path(tmp_evt.name)
        
    try:
        event_multipliers = loader.load_event_multipliers(evt_path)
        inventory_df = loader.load_inventory_sales(inv_path)
        
        if event_name not in event_multipliers:
            return jsonify({"error": f"Event '{event_name}' not found."}), 400
            
        event_multiplier = event_multipliers[event_name]
        rows = inventory_df[inventory_df["event_name"] == event_name]
        
        records = []
        for _, row in rows.iterrows():
            row_dict = row.to_dict()
            try:
                computed = engine.compute(row_dict, event_multiplier)
                tier = classifier.classify(computed)
                record = {
                    "style_number": row_dict["style_number"],
                    "event_name": row_dict["event_name"],
                    **computed,
                    **tier,
                }
                records.append(record)
            except Exception as e:
                continue
                
        # AI Generation via Groq
        if use_ai:
            from groq import Groq
            if not config.GROQ_API_KEY:
                return jsonify({"error": "GROQ_API_KEY is not set in the .env file. Add it or disable AI mode."}), 400
            groq_client = Groq(api_key=config.GROQ_API_KEY)
            for record in records:
                record["reason"] = ai_reason.generate_reason(record, client=groq_client)
        else:
            for record in records:
                record["reason"] = config.FALLBACK_REASON_TEMPLATES.get(
                    record["priority"], "Recommendation generated from current sales and stock data."
                )
                
        return jsonify({"records": records})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        os.unlink(inv_path)
        os.unlink(evt_path)

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    print("Starting Web Server at http://localhost:5000")
    app.run(debug=True, port=5000)
