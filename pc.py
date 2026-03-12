"""
CloudPrint — Printer Client
Runs on the machine connected to the printer.
Connects to the server via WebSocket, downloads, and prints files.
"""

import socketio
import requests
import os
import time
import platform
import subprocess

# ── Configuration ──────────────────────────────────────────────
#SERVER_URL   = 'https://laughing-bassoon-x5rqr4jj7646cvgwr-5000.app.github.dev/'
SERVER_URL   = 'https://cloud-print-2.onrender.com/'

PRINTER_ID   = 'printer-1'        # Must match one of the printer IDs in app.py
PRINTER_NAME = 'Office Printer'   # Display name

# Always store downloads next to this script — never in system temp
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
# ───────────────────────────────────────────────────────────────

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
print(f'[CloudPrint] Download folder: {DOWNLOAD_DIR}')

sio = socketio.Client()

@sio.event
def connect():
    print(f'[CloudPrint Client] Connected to {SERVER_URL}')
    print(f'[CloudPrint Client] Printer: {PRINTER_NAME} ({PRINTER_ID})')

@sio.event
def disconnect():
    print('[CloudPrint Client] Disconnected from server')

@sio.on('new_job')
def on_new_job(job):
    """Triggered when a new print job arrives."""
    if job.get('printer_id') != PRINTER_ID:
        return  # Not for this printer

    print(f"\n[NEW JOB] #{job['id']} — {job['file']}")
    print(f"  Copies: {job['copies']}, Color: {job['color']}, Pages: {job['page_range']}")

    # Download the file
    filepath = download_file(job)
    if not filepath:
        print(f"[ERROR] Failed to download file for job #{job['id']}")
        update_job_status(job['id'], 'failed')
        return

    # Report printing started
    update_job_status(job['id'], 'printing')

    # Print the file
    success = print_file(filepath, job)

    if success:
        update_job_status(job['id'], 'completed')
        print(f"[DONE] Job #{job['id']} printed successfully.")
    else:
        update_job_status(job['id'], 'failed')
        print(f"[ERROR] Failed to print job #{job['id']}")

    # Cleanup downloaded file after printing
    try:
        os.remove(filepath)
        print(f'[CLEANUP] Deleted {filepath}')
    except Exception as e:
        print(f'[WARN] Could not delete file: {e}')

def update_job_status(job_id, status):
    """Report job status back to the server."""
    try:
        res = requests.post(
            f'{SERVER_URL}/api/jobs/{job_id}/status',
            json={'status': status},
            timeout=10
        )
        print(f'[STATUS] Job #{job_id} -> {status} (HTTP {res.status_code})')
    except Exception as e:
        print(f'[WARN] Could not update job status: {e}')

def download_file(job):
    """Download the uploaded file from the server into DOWNLOAD_DIR."""
    filename = os.path.basename(job['filepath'])   # strip any path prefix
    url       = f"{SERVER_URL}/api/download/{filename}"
    save_path = os.path.join(DOWNLOAD_DIR, filename)

    print(f'[DOWNLOAD] Fetching {url}')
    print(f'[DOWNLOAD] Saving to {save_path}')

    try:
        res = requests.get(url, stream=True, timeout=30)
        print(f'[DOWNLOAD] HTTP {res.status_code}  Content-Type: {res.headers.get("Content-Type")}')

        if res.status_code == 200:
            with open(save_path, 'wb') as f:
                total = 0
                for chunk in res.iter_content(8192):
                    f.write(chunk)
                    total += len(chunk)
            print(f'[DOWNLOAD] Done — {total} bytes written to {save_path}')
            return save_path
        else:
            print(f'[ERROR] Server returned {res.status_code}: {res.text[:200]}')

    except requests.exceptions.ConnectionError:
        print(f'[ERROR] Cannot reach server at {SERVER_URL} — is it running?')
    except PermissionError:
        print(f'[ERROR] Permission denied writing to {save_path}')
    except Exception as e:
        print(f'[ERROR] Download failed: {type(e).__name__}: {e}')

    return None

def print_file(filepath, job):
    """Send file to printer based on OS."""
    copies = job.get('copies', 1)
    system = platform.system()

    try:
        if system == 'Windows':
            return print_windows(filepath, copies, job)
        elif system == 'Darwin':
            return print_macos(filepath, copies)
        elif system == 'Linux':
            return print_linux(filepath, copies)
        else:
            print(f'[WARN] Unsupported OS: {system}')
            return False
    except Exception as e:
        print(f'[ERROR] Printing failed: {e}')
        return False

def print_windows(filepath, copies, job):
    """Print using Windows Print Spooler via pywin32."""
    try:
        import win32api
        import win32print

        printer_name = win32print.GetDefaultPrinter()
        print(f'[WIN] Printing to: {printer_name}')

        for i in range(copies):
            win32api.ShellExecute(
                0, 'print', filepath, f'/d:"{printer_name}"', '.', 0
            )
            time.sleep(1)
        return True
    except ImportError:
        print('[WARN] pywin32 not installed. Simulating print...')
        time.sleep(2)
        return True

def print_macos(filepath, copies):
    """Print using lp command on macOS."""
    cmd = ['lp', '-n', str(copies), filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'[ERROR] lp error: {result.stderr}')
    return result.returncode == 0

def print_linux(filepath, copies):
    """Print using lp command on Linux (CUPS)."""
    cmd = ['lp', '-n', str(copies), filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'[ERROR] lp error: {result.stderr}')
    return result.returncode == 0

def poll_for_jobs():
    """Poll the server for waiting jobs assigned to this printer."""
    try:
        res = requests.get(f'{SERVER_URL}/api/jobs', timeout=10)
        jobs = res.json()
        waiting = [j for j in jobs if j['status'] == 'waiting' and j['printer_id'] == PRINTER_ID]
        if waiting:
            print(f'[POLL] Found {len(waiting)} waiting job(s)')
        for job in waiting:
            on_new_job(job)
    except Exception as e:
        print(f'[WARN] Poll failed: {e}')

def main():
    print('═══════════════════════════════════')
    print('  CloudPrint Printer Client v2.0   ')
    print('═══════════════════════════════════')
    print(f'Server      : {SERVER_URL}')
    print(f'Printer     : {PRINTER_NAME} ({PRINTER_ID})')
    print(f'OS          : {platform.system()}')
    print(f'Download dir: {DOWNLOAD_DIR}')
    print('───────────────────────────────────')

    try:
        sio.connect(SERVER_URL)
        print('[OK] WebSocket connected. Waiting for jobs...\n')
        poll_for_jobs()
        sio.wait()
    except Exception as e:
        print(f'[ERROR] Could not connect to server: {e}')
        print('Retrying in 5 seconds...')
        time.sleep(5)
        main()

if __name__ == '__main__':
    main()
