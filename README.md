# ◈ CloudPrint — Cloud-Based Printing System

A modern, real-time cloud printing system built with Flask and WebSockets.

---

## 📁 Project Structure

```
cloud-print/
├── app.py                  ← Flask web server (main entry point)
├── printer_client.py       ← Client script (runs on printer machine)
├── requirements.txt        ← Python dependencies
├── templates/
│   ├── index.html          ← Upload page
│   └── dashboard.html      ← Live dashboard
├── static/
│   ├── css/
│   │   ├── main.css        ← Main styles
│   │   └── dashboard.css   ← Dashboard styles
│   └── js/
│       ├── main.js         ← Upload page logic
│       └── dashboard.js    ← Dashboard logic
├── uploads/                ← Temporary uploaded files
└── printed/                ← Files being printed (auto-cleaned after 24h)
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python app.py
```

Server runs at: **http://localhost:5000**

### 3. Start the Printer Client

On the machine connected to the printer:

```bash
python printer_client.py
```

---

## 🌐 Pages

| Page | URL | Description |
|------|-----|-------------|
| Upload | `/` | Upload files and configure print settings |
| Dashboard | `/dashboard` | Real-time monitoring of all print jobs |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a file and create a print job |
| `GET` | `/api/jobs` | Get all print jobs |
| `GET` | `/api/jobs/<id>` | Get a specific job |
| `POST` | `/api/jobs/<id>/cancel` | Cancel a waiting job |
| `GET` | `/api/printers` | List all printers |
| `GET` | `/api/stats` | Get job statistics |

### Upload Parameters (multipart/form-data)
- `file` — PDF, JPG, or PNG (max 50MB)
- `copies` — Number of copies (default: 1)
- `printer_id` — Printer ID (printer-1, printer-2, printer-3)
- `color` — `bw` or `color`
- `page_range` — `all`, `odd`, `even`, or `custom`

---

## 🔧 WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `new_job` | Server → Client | New print job created |
| `job_updated` | Server → Client | Job status changed |
| `printer_updated` | Server → Client | Printer status changed |

---

## ⚙ Printer Configuration

Edit `printer_client.py` to configure:

```python
SERVER_URL   = 'http://localhost:5000'  # Your server URL
PRINTER_ID   = 'printer-1'             # Which printer this client handles
PRINTER_NAME = 'Office Printer'        # Display name
```

### OS Support
- **Windows** — Uses Windows Print Spooler via `pywin32`
- **macOS** — Uses `lp` command (CUPS)
- **Linux** — Uses `lp` command (CUPS)

---

## 🔒 Security (Production)

Add these before deploying:

1. **Authentication** — Add Flask-Login or Flask-JWT
2. **HTTPS** — Use Nginx + Let's Encrypt
3. **File validation** — Already included (type + size limits)
4. **Rate limiting** — Add Flask-Limiter
5. **Database** — Replace in-memory store with SQLAlchemy + PostgreSQL

---

## 📦 Production with Gunicorn

```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:5000
```

---

## 🔮 Future Features

- [ ] User login & accounts
- [ ] Payment gateway for print shops
- [ ] PDF preview before printing
- [ ] Print history & logs
- [ ] QR code generation for pickup
- [ ] Email-to-print feature
- [ ] Mobile app (React Native)