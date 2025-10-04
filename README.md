# Real Estate Listings Portal

A Flask web app for managing and searching real estate listings across the Canberra region.

Features:
- Upload listing spreadsheets (CSV) with property details and agent initials
- Manage agent profiles with contact info and office assignment
- Enrich listings with images, descriptions, and links
- Flag listings where agents need help finding buyers
- Search listings by suburb, office, or agent

Run locally:
```
python -m venv .venv
source .venv/bin/activate  # (or .venv\Scripts\Activate.ps1 on Windows)
pip install -r requirements.txt
flask --app app.app run --debug
```
Then open http://127.0.0.1:5000/