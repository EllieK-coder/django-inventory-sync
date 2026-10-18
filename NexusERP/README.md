# NexusERP

Nexus ERP Backend System — a standalone logistics platform built with Django and Django REST Framework, designed to handle automated third-party REST API synchronization workflows.

## Features
- **Live Sync Engine:** Handshakes with external data provider streams to parse and update local relational tables dynamically.
- **Full CRUD Management:** Interactive dark-mode user dashboards for manual stock entry modifications and removal protocols.
- **Serialized API Layer:** Fully exposed operational REST API endpoint producing structured JSON inventory payloads.

## Getting started

Requires Python 3.12+.

```bash
git clone https://github.com/EllieK-coder/NexusERP.git
cd NexusERP

python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

## Pages

| URL | What it does |
|---|---|
| `/home/` | Dashboard |
| `/list/` | Product list |
| `/add/`, `/edit/<id>/`, `/delete/<id>/` | Create, update, delete products |
| `/sync/` | Pull items from the external API into the database |
| `/api/products/` | JSON list of all products |
| `/admin/` | Django admin (create a user with `python manage.py createsuperuser`) |
