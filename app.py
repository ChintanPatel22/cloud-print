import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import os
import uuid
import json
import time
import threading
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

#from flask import Flask, render_template, request, jsonify, send_from_directory
#from flask_socketio import SocketIO, emit
#import os
"""
import uuid
import json
import time
import threading
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
"""

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cloudprint-secret-2024'

# Use absolute paths so files are always found regardless of working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['PRINTED_FOLDER'] = os.path.join(BASE_DIR, 'printed')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory job store (use a database in production)
print_jobs = {}
printers = {
    'printer-1': {'name': 'Office Printer', 'status': 'online', 'jobs': 0, 'color': True},
    'printer-2': {'name': 'Color Printer', 'status': 'online', 'jobs': 0, 'color': True},
    'printer-3': {'name': 'Large Format Printer', 'status': 'offline', 'jobs': 0, 'color': False},
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def simulate_printing(job_id):
    """Simulate the printing process with status updates."""
    time.sleep(2)
    if job_id in print_jobs:
        print_jobs[job_id]['status'] = 'printing'
        print_jobs[job_id]['updated_at'] = datetime.now().isoformat()
        socketio.emit('job_updated', print_jobs[job_id])

        printer_id = print_jobs[job_id].get('printer_id')
        if printer_id in printers:
            printers[printer_id]['jobs'] += 1

        time.sleep(3)

        if job_id in print_jobs:
            print_jobs[job_id]['status'] = 'completed'
            print_jobs[job_id]['updated_at'] = datetime.now().isoformat()
            socketio.emit('job_updated', print_jobs[job_id])

            if printer_id in printers:
                printers[printer_id]['jobs'] = max(0, printers[printer_id]['jobs'] - 1)

            socketio.emit('printer_updated', {'id': printer_id, **printers[printer_id]})

def cleanup_old_files():
    """Remove files older than 24 hours from printed folder."""
    while True:
        time.sleep(3600)  # Run every hour
        cutoff = datetime.now() - timedelta(hours=24)
        folder = app.config['PRINTED_FOLDER']
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff:
                        os.remove(filepath)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PDF, JPG, or PNG.'}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)

    job_id = str(uuid.uuid4().hex[:8].upper())
    job = {
        'id': job_id,
        'file': filename,
        'filepath': unique_filename,
        'status': 'waiting',
        'copies': int(request.form.get('copies', 1)),
        'printer_id': request.form.get('printer_id', 'printer-1'),
        'printer_name': printers.get(request.form.get('printer_id', 'printer-1'), {}).get('name', 'Office Printer'),
        'color': request.form.get('color', 'bw'),
        'page_range': request.form.get('page_range', 'all'),
        'file_size': os.path.getsize(filepath),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }

    print_jobs[job_id] = job
    socketio.emit('new_job', job)

    # Start printing simulation in background
    thread = threading.Thread(target=simulate_printing, args=(job_id,))
    thread.daemon = True
    thread.start()

    return jsonify({'success': True, 'job': job})

@app.route('/api/jobs')
def get_jobs():
    jobs_list = list(print_jobs.values())
    jobs_list.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(jobs_list)

@app.route('/api/jobs/<job_id>')
def get_job(job_id):
    job = print_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    job = print_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job['status'] == 'waiting':
        job['status'] = 'cancelled'
        job['updated_at'] = datetime.now().isoformat()
        socketio.emit('job_updated', job)
        return jsonify({'success': True, 'job': job})
    return jsonify({'error': 'Cannot cancel job in current state'}), 400

@app.route('/api/download/<filename>')
def download_file(filename):
    """Printer client calls this to fetch the uploaded file."""
    safe_name = secure_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)

    if not os.path.isfile(file_path):
        return jsonify({'error': f'File not found: {safe_name}'}), 404

    # Detect correct MIME type so Adobe / OS opens it properly
    ext = safe_name.rsplit('.', 1)[-1].lower()
    mime_map = {
        'pdf':  'application/pdf',
        'jpg':  'image/jpeg',
        'jpeg': 'image/jpeg',
        'png':  'image/png',
    }
    mimetype = mime_map.get(ext, 'application/octet-stream')

    # as_attachment=False lets Adobe open inline; True forces a download prompt
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        safe_name,
        mimetype=mimetype,
        as_attachment=False
    )

@app.route('/api/jobs/<job_id>/status', methods=['POST'])
def update_job_status(job_id):
    """Printer client calls this to report real print status."""
    job = print_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    allowed = {'printing', 'completed', 'failed'}
    if new_status not in allowed:
        return jsonify({'error': f'Status must be one of: {allowed}'}), 400
    job['status'] = new_status
    job['updated_at'] = datetime.now().isoformat()
    socketio.emit('job_updated', job)
    return jsonify({'success': True, 'job': job})

@app.route('/api/printers')
def get_printers():
    printers_list = [{'id': k, **v} for k, v in printers.items()]
    return jsonify(printers_list)

@app.route('/api/stats')
def get_stats():
    all_jobs = list(print_jobs.values())
    return jsonify({
        'total': len(all_jobs),
        'waiting': sum(1 for j in all_jobs if j['status'] == 'waiting'),
        'printing': sum(1 for j in all_jobs if j['status'] == 'printing'),
        'completed': sum(1 for j in all_jobs if j['status'] == 'completed'),
        'cancelled': sum(1 for j in all_jobs if j['status'] == 'cancelled'),
    })

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'ok'})

#if __name__ == '__main__':
  #  os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
  #  os.makedirs(app.config['PRINTED_FOLDER'], exist_ok=True)
  #  socketio.run(app, debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
