import os, csv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from .models import db, Agent, Listing, ListingImage, OFFICES

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portal.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'app/static/uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)

    @app.cli.command('db-init')
    def db_init():
        with app.app_context():
            db.create_all()
            print('✅ Database initialised')

    @app.route('/')
    def index():
        q = request.args.get('q','').strip().lower()
        office = request.args.get('office','').strip()
        suburb = request.args.get('suburb','').strip().lower()
        needs = request.args.get('needs','').strip().lower()

        query = Listing.query
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(Listing.address.ilike(like), Listing.development.ilike(like))
            )
        if office:
            query = query.filter(Listing.office==office)
        if suburb:
            like = f"%{suburb}%"
            query = query.filter(Listing.suburb.ilike(like))
        if needs == 'yes':
            query = query.filter(Listing.needs_buyers.is_(True))
        elif needs == 'no':
            query = query.filter(Listing.needs_buyers.is_(False))

        listings = query.order_by(Listing.created_at.desc()).limit(200).all()
        return render_template('index.html', listings=listings, offices=OFFICES)

    @app.route('/admin')
    def admin():
        return render_template('admin.html')

    EXPECTED = ['date','time','address','development','suburb','seen','price','agent','office','com','type','bed','bath','gar','land','access','single level','RZ zoning','auctioneer']

    def parse_bool(v):
        if v is None: return None
        s = str(v).strip().lower()
        if s in ('1','true','yes','y','t'): return True
        if s in ('0','false','no','n','f'): return False
        return None

    def parse_int(v):
        try:
            return int(float(str(v).strip()))
        except Exception:
            return None

    @app.route('/admin/upload', methods=['GET', 'POST'])
    def upload():
        if request.method == 'POST':
            file = request.files.get('csv')
            if not file:
                flash('No file selected', 'error')
                return redirect(request.url)

            # Read CSV text; tolerate BOM and weird encodings
            text = file.stream.read().decode('utf-8-sig', errors='ignore')
            rows = list(csv.DictReader(text.splitlines()))
            if not rows:
                flash('CSV appears empty', 'error')
                return redirect(request.url)

            # ✅ Option C: trim header spaces, ignore any extra columns after the first 19
            EXPECTED = [
                'date', 'time', 'address', 'development', 'suburb', 'seen', 'price', 'agent', 'office', 'com',
                'type', 'bed', 'bath', 'gar', 'land', 'access', 'single level', 'rz zoning', 'auctioneer'
            ]
            headers = [h.strip() for h in rows[0].keys()]  # trim spaces in header cells
            first_19 = [h.lower() for h in headers[:len(EXPECTED)]]  # normalise case for first 19

            if first_19 != EXPECTED:
                flash('CSV headers do not match expected format (first 19 columns).', 'error')
                return redirect(request.url)

            def parse_bool(v):
                if v is None:
                    return None
                s = str(v).strip().lower()
                if s in ('1', 'true', 'yes', 'y', 't'):
                    return True
                if s in ('0', 'false', 'no', 'n', 'f'):
                    return False
                return None

            def parse_int(v):
                try:
                    return int(float(str(v).strip()))
                except Exception:
                    return None

            added = updated = 0
            for r in rows:
                # Normalise keys (strip spaces, lower case)
                row = {
                    (k.strip().lower() if k is not None else k): (v.strip() if isinstance(v, str) else v)
                    for k, v in r.items()
                }

                address = row.get('address')
                if not address:
                    continue

                listing = Listing.query.filter_by(address=address).first()
                creating = False
                if not listing:
                    listing = Listing(address=address)
                    creating = True

                # Map fields (with tolerant fallbacks: 'land ' → 'land', 'RZ zoning' variants)
                listing.date = row.get('date')
                listing.time = row.get('time')
                listing.development = row.get('development')
                listing.suburb = row.get('suburb')
                listing.seen = bool(parse_bool(row.get('seen')))
                listing.price = row.get('price')
                listing.agent_initials = row.get('agent')
                listing.office = row.get('office')
                listing.com = bool(parse_bool(row.get('com')))
                listing.type = row.get('type')
                listing.bed = parse_int(row.get('bed'))
                listing.bath = parse_int(row.get('bath'))
                listing.gar = parse_int(row.get('gar'))
                listing.land = row.get('land') or row.get('land ')
                listing.access = row.get('access')
                listing.single_level = bool(parse_bool(row.get('single level')))
                listing.rz_zoning = (
                    row.get('rz zoning')
                    or row.get('rz zoning ')
                    or row.get('rz zoning')
                    or row.get('rz zoning ')
                )
                listing.auctioneer = row.get('auctioneer')

                # Link agent by initials if profile exists
                if listing.agent_initials:
                    agent = Agent.query.filter_by(initials=listing.agent_initials).first()
                    if agent:
                        listing.agent = agent

                if creating:
                    db.session.add(listing)
                    added += 1
                else:
                    updated += 1

            db.session.commit()
            flash(f'Imported {len(rows)} rows (added {added}, updated {updated}).', 'success')
            return redirect(url_for('manage_listings'))

        return render_template('upload.html')
    @app.route('/admin/agents', methods=['GET','POST'])
    def manage_agents():
        if request.method == 'POST':
            initials = request.form.get('initials','').strip().upper()
            if not initials:
                flash('Initials required','error')
                return redirect(request.url)
            agent = Agent.query.filter_by(initials=initials).first()
            if not agent:
                agent = Agent(initials=initials)
                db.session.add(agent)
            agent.first_name = request.form.get('first_name')
            agent.last_name = request.form.get('last_name')
            agent.email = request.form.get('email')
            agent.phone = request.form.get('phone')
            office = request.form.get('office')
            if office in OFFICES:
                agent.office = office
            db.session.commit()
            flash('Agent saved','success')
            return redirect(request.url)

        agents = Agent.query.order_by(Agent.initials.asc()).all()
        return render_template('agents.html', agents=agents, offices=OFFICES)

    @app.route('/admin/listings')
    def manage_listings():
        listings = Listing.query.order_by(Listing.created_at.desc()).all()
        return render_template('manage_listings.html', listings=listings)

    @app.route('/admin/listings/<int:listing_id>/edit', methods=['GET','POST'])
    def edit_listing(listing_id):
        l = Listing.query.get_or_404(listing_id)
        if request.method == 'POST':
            l.listing_url = request.form.get('listing_url')
            l.description = request.form.get('description')
            l.needs_buyers = True if request.form.get('needs_buyers') == 'on' else False

            # images
            files = request.files.getlist('images')
            for f in files:
                if not f or f.filename == '':
                    continue
                name = secure_filename(f.filename)
                base, ext = os.path.splitext(name)
                final = name
                i = 1
                while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], final)):
                    final = f"{base}_{i}{ext}"
                    i += 1
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], final))
                db.session.add(ListingImage(listing_id=l.id, path=final))

            db.session.commit()
            flash('Listing updated','success')
            return redirect(url_for('manage_listings'))

        return render_template('edit_listing.html', listing=l)

    return app

app = create_app()
