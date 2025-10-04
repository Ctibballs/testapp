# Real Estate Listings Portal

This project provides an internal web portal for managing and searching real estate listings across the Canberra region.

## Features

- Upload listing spreadsheets (CSV) with auction details, compliance status, property specs, and agent initials.
- Manage agent profiles linked to the initials used in spreadsheets, including contact details and office assignment.
- Enrich listings with descriptions, links, and image galleries.
- Flag listings where agents need help finding a buyer and allow agents to filter by these opportunities.
- Search listings by suburb/region and view agent contact information.

## Technology

- Python 3.11+
- Flask & Flask-SQLAlchemy
- SQLite database (default)

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the application**

   ```bash
   flask --app app.app run --debug
   ```

   The site will be available at <http://127.0.0.1:5000/>.

3. **Upload listings**

   - Prepare a CSV file that includes the following column headers exactly as written:
     `date`, `time`, `address`, `development`, `suburb`, `seen`, `price`, `agent`, `office`, `com`, `type`, `bed`, `bath`, `gar`, `land`, `access`, `single level`, `RZ zoning`, `auctioneer`.
   - Navigate to **Admin → Upload Spreadsheet** to import listing data. Existing listings are matched by address.

4. **Manage agents**

   - Go to **Admin → Manage Agents** to create or update agent profiles. Ensure the initials match those found in spreadsheets so listings link correctly.

5. **Edit listings**

   - After importing, open **Admin → Manage Listings** to add descriptions, upload images, paste listing links, and toggle the "needs buyers" flag.

## File uploads

Uploaded images are stored in `app/static/uploads`. Ensure this directory is writable on the deployment server.

## Environment configuration

Set the `SQLALCHEMY_DATABASE_URI` environment variable before launching the app to use an alternative database backend if required.
