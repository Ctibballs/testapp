# Real Estate Listings Portal (Full)

Internal portal for Canberra network listings.

## Features
- Upload CSV with headers: `date,time,address,development,suburb,seen,price,agent,office,com,type,bed,bath,gar,land,access,single level,RZ zoning,auctioneer`
- Manage agents (initials → contact details, office)
- Edit listings: description, listing URL, images
- "Needs buyers" flag + filter
- Search by office, suburb/region, keyword, needs buyers

## Getting Started

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
flask --app app.app db-init
flask --app app.app run --debug
```

Open http://127.0.0.1:5000/
