from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from .models import Agent, Listing, ListingImage, db

UPLOAD_SUBDIR = Path("uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
OFFICES = [
    "Kippax",
    "Kaleen",
    "Canberra City",
    "Gungahlin",
    "Tuggeranong",
    "Dickson",
    "Woden/Weston",
    "Country",
    "Projects",
]


def create_app(database_uri: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri or "sqlite:///realestate.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    upload_folder = Path(app.root_path) / "static" / UPLOAD_SUBDIR
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_folder)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_positive_int(raw_value: str | None) -> int | None:
    if raw_value is None or raw_value == "":
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _extract_numeric(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _extract_price(value: str | None) -> int | None:
    numeric = _extract_numeric(value)
    if numeric is None:
        return None
    return int(round(numeric))


def _matches_numeric_filters(
    listing: Listing,
    *,
    bedrooms: int | None,
    bathrooms: int | None,
    garages: int | None,
    price_min: int | None,
    price_max: int | None,
) -> bool:
    bed_value = _extract_numeric(listing.bed)
    if bedrooms is not None and (bed_value is None or bed_value < bedrooms):
        return False

    bath_value = _extract_numeric(listing.bath)
    if bathrooms is not None and (bath_value is None or bath_value < bathrooms):
        return False

    gar_value = _extract_numeric(listing.gar)
    if garages is not None and (gar_value is None or gar_value < garages):
        return False

    price_value = _extract_price(listing.price)
    if price_min is not None and (price_value is None or price_value < price_min):
        return False
    if price_max is not None and (price_value is None or price_value > price_max):
        return False

    return True


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        filters = {
            "needs_help": request.args.get("needs_help") == "on",
            "suburb": request.args.get("suburb", "").strip(),
            "bedrooms": _parse_positive_int(request.args.get("bedrooms")),
            "bathrooms": _parse_positive_int(request.args.get("bathrooms")),
            "garages": _parse_positive_int(request.args.get("garages")),
            "price_min": _parse_positive_int(request.args.get("price_min")),
            "price_max": _parse_positive_int(request.args.get("price_max")),
            "property_type": request.args.get("property_type", "").strip(),
            "office": request.args.get("office", "").strip(),
        }

        query = Listing.query
        if filters["needs_help"]:
            query = query.filter_by(needs_help=True)
        if filters["suburb"]:
            query = query.filter(Listing.suburb.ilike(f"%{filters['suburb']}%"))
        if filters["property_type"]:
            query = query.filter(Listing.property_type.ilike(f"%{filters['property_type']}%"))
        if filters["office"]:
            query = query.filter(Listing.office == filters["office"])

        listings = query.order_by(Listing.date.asc().nullslast()).all()

        listings = [
            listing
            for listing in listings
            if _matches_numeric_filters(
                listing,
                bedrooms=filters["bedrooms"],
                bathrooms=filters["bathrooms"],
                garages=filters["garages"],
                price_min=filters["price_min"],
                price_max=filters["price_max"],
            )
        ]

        property_types = [
            row[0]
            for row in db.session.query(Listing.property_type)
            .filter(Listing.property_type.isnot(None))
            .filter(Listing.property_type != "")
            .distinct()
            .order_by(Listing.property_type.asc())
            .all()
        ]
        offices = OFFICES

        return render_template(
            "index.html",
            listings=listings,
            filters=filters,
            property_types=property_types,
            offices=offices,
        )

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/admin")
    def admin_dashboard():
        return render_template("admin/dashboard.html", agent_count=Agent.query.count(), listing_count=Listing.query.count())

    @app.route("/admin/agents", methods=["GET", "POST"])
    def manage_agents():
        if request.method == "POST":
            initials = request.form.get("initials", "").strip().upper()
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            office = request.form.get("office", OFFICES[0])

            if not initials or not name:
                flash("Initials and name are required for agents.", "error")
            else:
                agent = Agent.query.filter_by(initials=initials).first()
                if agent:
                    agent.name = name
                    agent.email = email
                    agent.phone = phone
                    agent.office = office
                    flash("Updated existing agent profile.", "success")
                else:
                    agent = Agent(
                        initials=initials,
                        name=name,
                        email=email or None,
                        phone=phone or None,
                        office=office,
                    )
                    db.session.add(agent)
                    flash("Created new agent profile.", "success")
                db.session.commit()
            return redirect(url_for("manage_agents"))

        agents = Agent.query.order_by(Agent.initials.asc()).all()
        return render_template("admin/agents.html", agents=agents, offices=OFFICES)

    @app.route("/admin/agents/<int:agent_id>/delete", methods=["POST"])
    def delete_agent(agent_id: int):
        agent = Agent.query.get_or_404(agent_id)
        if agent.listings:
            flash("Cannot delete an agent who has listings assigned.", "error")
        else:
            db.session.delete(agent)
            db.session.commit()
            flash("Agent deleted.", "success")
        return redirect(url_for("manage_agents"))

    @app.route("/admin/upload", methods=["GET", "POST"])
    def upload_listings():
        if request.method == "POST":
            file = request.files.get("spreadsheet")
            if not file or file.filename == "":
                flash("Please select a spreadsheet to upload.", "error")
                return redirect(request.url)

            try:
                records = parse_spreadsheet(file.stream.read().decode("utf-8", errors="ignore").splitlines())
            except Exception as exc:  # pragma: no cover - defensive fallback
                flash(f"Could not parse spreadsheet: {exc}", "error")
                return redirect(request.url)

            created = 0
            for record in records:
                listing = Listing.query.filter_by(address=record.get("address")).first()
                if listing:
                    apply_listing_record(listing, record)
                else:
                    listing = Listing()
                    apply_listing_record(listing, record)
                    db.session.add(listing)
                    created += 1
            db.session.commit()
            flash(f"Processed {len(records)} listings ({created} new).", "success")
            return redirect(url_for("list_admin_listings"))

        return render_template("admin/upload.html")

    @app.route("/admin/listings")
    def list_admin_listings():
        listings = Listing.query.order_by(Listing.date.desc().nullslast()).all()
        return render_template("admin/listings.html", listings=listings)

    @app.route("/admin/listings/<int:listing_id>", methods=["GET", "POST"])
    def edit_listing(listing_id: int):
        listing = Listing.query.get_or_404(listing_id)
        if request.method == "POST":
            listing.description = request.form.get("description", "").strip() or None
            listing.listing_link = request.form.get("listing_link", "").strip() or None
            listing.needs_help = bool(request.form.get("needs_help"))

            if request.form.get("agent_id"):
                listing.agent_id = int(request.form["agent_id"])
            else:
                listing.agent_id = None

            db.session.commit()
            flash("Listing details updated.", "success")
            return redirect(request.url)

        return render_template("admin/edit_listing.html", listing=listing, agents=Agent.query.order_by(Agent.initials).all())

    @app.route("/admin/listings/<int:listing_id>/images", methods=["POST"])
    def upload_listing_image(listing_id: int):
        listing = Listing.query.get_or_404(listing_id)
        file = request.files.get("image")
        if not file or file.filename == "":
            flash("Select an image to upload.", "error")
            return redirect(url_for("edit_listing", listing_id=listing_id))
        if not allowed_file(file.filename):
            flash("Unsupported file type. Please upload an image.", "error")
            return redirect(url_for("edit_listing", listing_id=listing_id))

        filename = secure_filename(file.filename)
        upload_dir = Path(app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / filename
        counter = 1
        while path.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            filename = f"{stem}_{counter}{suffix}"
            path = upload_dir / filename
            counter += 1
        file.save(path)

        image = ListingImage(filename=filename, listing=listing)
        db.session.add(image)
        db.session.commit()
        flash("Image uploaded.", "success")
        return redirect(url_for("edit_listing", listing_id=listing_id))

    @app.route("/listings/<int:listing_id>")
    def listing_detail(listing_id: int):
        listing = Listing.query.get_or_404(listing_id)
        return render_template("listings/detail.html", listing=listing, offices=OFFICES)

    @app.route("/admin/listings/<int:listing_id>/images/<int:image_id>/delete", methods=["POST"])
    def delete_listing_image(listing_id: int, image_id: int):
        listing = Listing.query.get_or_404(listing_id)
        image = ListingImage.query.filter_by(id=image_id, listing=listing).first_or_404()
        try:
            os.remove(Path(app.config["UPLOAD_FOLDER"]) / image.filename)
        except FileNotFoundError:  # pragma: no cover - safe cleanup if file missing
            pass
        db.session.delete(image)
        db.session.commit()
        flash("Image removed.", "success")
        return redirect(url_for("edit_listing", listing_id=listing_id))


def parse_spreadsheet(lines: Iterable[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(lines)
    expected_columns = {
        "date",
        "time",
        "address",
        "development",
        "suburb",
        "seen",
        "price",
        "agent",
        "office",
        "com",
        "type",
        "bed",
        "bath",
        "gar",
        "land",
        "access",
        "single level",
        "RZ zoning",
        "auctioneer",
    }
    missing = expected_columns - {name.strip() for name in reader.fieldnames or []}
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    records: list[dict[str, str]] = []
    for row in reader:
        record = {key.strip().lower(): (value.strip() if value else "") for key, value in row.items()}
        records.append(record)
    return records


def apply_listing_record(listing: Listing, record: dict[str, str]) -> None:
    agent_initials = record.get("agent", "").upper()
    listing.agent_initials = agent_initials or None
    agent = Agent.query.filter_by(initials=agent_initials).first() if agent_initials else None
    listing.agent = agent

    listing.date = parse_date(record.get("date"))
    listing.time = record.get("time") or None
    listing.address = record.get("address") or listing.address
    listing.development = record.get("development") or None
    listing.suburb = record.get("suburb") or None
    listing.seen = record.get("seen") or None
    listing.price = record.get("price") or None
    listing.office = record.get("office") or None
    listing.compliant = record.get("com") or None
    listing.property_type = record.get("type") or None
    listing.bed = record.get("bed") or None
    listing.bath = record.get("bath") or None
    listing.gar = record.get("gar") or None
    listing.land = record.get("land") or None
    listing.access = record.get("access") or None
    listing.single_level = record.get("single level") or None
    listing.rz_zoning = record.get("rz zoning") or None
    listing.auctioneer = record.get("auctioneer") or None

    listing.description = listing.description or None
    listing.listing_link = listing.listing_link or None
