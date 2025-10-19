# Virtual Home Appraisal

A lightweight Flask application that helps home owners prepare for a virtual appraisal. It combines known listing data with owner supplied information to build an indicative price estimate and surface relevant comparable sales.

## Key features

- 🔍 **Smart address lookup** – search from recent local listings to auto-fill suburb, bedroom, bathroom and parking details when the property is known.
- 🏡 **Property detail capture** – record the core property specs including land size and building age, along with feature checklists such as pools, solar, tennis courts and more.
- ⭐ **Quality scoring** – rate the condition of kitchens, bathrooms, living spaces, exterior and energy efficiency to influence the estimate multiplier.
- 📊 **Comparable sales context** – display recent suburb sales used to anchor the estimate so owners can sanity check assumptions.
- 🧮 **Transparent estimate breakdown** – show the baseline price, applied multipliers and adjustments for full visibility of how the indicative value was derived.

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the development server**

   ```bash
   flask --app app.app run --debug
   ```

   The site will be available at <http://127.0.0.1:5000/>.

3. **Try the appraisal workflow**

   - Begin typing an address and choose one of the suggested properties to pre-fill known data.
   - Update the bedrooms, bathrooms, land size and building age to reflect the current home.
   - Tick any standout features and rate the quality of key areas of the property.
   - Submit the form to generate an indicative price and review the comparable sales powering the result.

## Data source

The application ships with `listings.csv`, a sample set of ACT property sales used for auto-fill and comparable analysis. You can replace this file with your own dataset provided the CSV contains at least the columns `date`, `address`, `suburb`, `price`, `bed`, `bath`, `gar`, and `land`.

## Notes & next steps

- The quality ratings currently drive a simple multiplier; future iterations can introduce separate visuals for each quality tier.
- Feature adjustments are rule-of-thumb figures for the MVP. Adjust the values in `app/app.py` to match your market assumptions.
- Integrate third-party APIs (e.g. CoreLogic, Domain) to replace the static CSV with live sales and richer property metadata when credentials are available.
