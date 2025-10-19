from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable, List, Sequence

from flask import Flask, jsonify, render_template, request

DATA_PATH = Path(__file__).resolve().parent.parent / "listings.csv"

QUALITY_LEVELS = [
    {"id": "original_poor", "label": "Original – needs work", "multiplier": 0.90},
    {"id": "original_sound", "label": "Original – good condition", "multiplier": 1.00},
    {"id": "updated", "label": "Updated", "multiplier": 1.05},
    {"id": "renovated_premium", "label": "Renovated with premium finishes", "multiplier": 1.12},
]

QUALITY_SECTIONS = [
    {"id": "kitchen", "label": "Kitchen"},
    {"id": "bathrooms", "label": "Bathrooms"},
    {"id": "living_areas", "label": "Living areas"},
    {"id": "exterior", "label": "Exterior"},
    {"id": "energy", "label": "Energy efficiency"},
]

FEATURE_OPTIONS = [
    {"id": "pool", "label": "Swimming pool", "adjustment": 35000},
    {"id": "tennis", "label": "Tennis court", "adjustment": 45000},
    {"id": "solar", "label": "Solar panels", "adjustment": 12000},
    {"id": "batteries", "label": "Home battery system", "adjustment": 18000},
    {"id": "ducted_ac", "label": "Ducted A/C", "adjustment": 8000},
    {"id": "split_ac", "label": "Split system A/C", "adjustment": 4000},
    {"id": "double_glazing", "label": "Double glazing", "adjustment": 9000},
    {"id": "water_tank", "label": "Rainwater tank", "adjustment": 3000},
]


@dataclass
class PropertyRecord:
    address: str
    suburb: str
    bedrooms: int | None
    bathrooms: int | None
    parking: int | None
    price: int | None
    land_size: float | None
    date: datetime | None

    def serialize(self) -> dict[str, str | int | float | None]:
        return {
            "address": self.address,
            "suburb": self.suburb,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "parking": self.parking,
            "price": self.price,
            "land_size": self.land_size,
            "date": self.date.isoformat() if self.date else None,
        }


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_price(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("$", "").replace(",", "")
    cleaned = cleaned.replace("auction", "")
    cleaned = cleaned.replace("guide", "")
    cleaned = cleaned.replace("prior", "")
    cleaned = cleaned.replace("offers", "")
    cleaned = cleaned.replace("auction", "")
    cleaned = cleaned.replace("tba", "")
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    multiplier = 1
    if cleaned.endswith("m"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("mil"):
        multiplier = 1_000_000
        cleaned = cleaned[:-3]
    elif cleaned.endswith("k"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    cleaned = cleaned.strip("+").strip()
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        numeric_value = float(match.group())
        if multiplier == 1:
            if numeric_value < 10:
                numeric_value *= 1_000_000
            elif numeric_value < 10_000:
                numeric_value *= 1_000
        return int(numeric_value * multiplier)
    except ValueError:
        return None


def parse_land_size(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.lower().replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def load_property_records() -> list[PropertyRecord]:
    records: list[PropertyRecord] = []
    with DATA_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            records.append(
                PropertyRecord(
                    address=row.get("address", "").strip(),
                    suburb=row.get("suburb", "").strip(),
                    bedrooms=parse_int(row.get("bed")),
                    bathrooms=parse_int(row.get("bath")),
                    parking=parse_int(row.get("gar")),
                    price=parse_price(row.get("price")),
                    land_size=parse_land_size(row.get("land")),
                    date=parse_date(row.get("date")),
                )
            )
    return records


def currency(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.0f}"


def average_price(records: Iterable[PropertyRecord]) -> float | None:
    prices = [record.price for record in records if record.price]
    if not prices:
        return None
    return mean(prices)


def average_land(records: Iterable[PropertyRecord]) -> float | None:
    land_values = [record.land_size for record in records if record.land_size]
    if not land_values:
        return None
    return mean(land_values)


def find_recent_sales(records: Sequence[PropertyRecord], suburb: str, limit: int = 5) -> list[PropertyRecord]:
    suburb_records = [r for r in records if r.suburb.lower() == suburb.lower() and r.price]
    suburb_records.sort(key=lambda r: (r.date or datetime.min), reverse=True)
    return suburb_records[:limit]


def select_comparables(records: Sequence[PropertyRecord], suburb: str, bedrooms: int | None) -> list[PropertyRecord]:
    suburb_records = [r for r in records if r.suburb.lower() == suburb.lower() and r.price]
    if bedrooms is not None:
        exact = [r for r in suburb_records if r.bedrooms == bedrooms]
        if exact:
            suburb_records = exact
    return suburb_records


def calculate_estimate(
    *,
    all_records: Sequence[PropertyRecord],
    suburb: str,
    bedrooms: int | None,
    bathrooms: int | None,
    parking: int | None,
    land_size: float | None,
    building_age: int | None,
    quality_choices: dict[str, str],
    selected_features: list[str],
) -> dict[str, object]:
    comparables = select_comparables(all_records, suburb, bedrooms) if suburb else []
    base_price = average_price(comparables) or average_price(all_records)
    if base_price is None:
        base_price = 0

    quality_map = {level["id"]: level["multiplier"] for level in QUALITY_LEVELS}
    selected_multipliers = [
        quality_map.get(choice, 1.0)
        for choice in quality_choices.values()
        if choice in quality_map
    ]
    quality_multiplier = mean(selected_multipliers) if selected_multipliers else 1.0

    feature_adjustments = {
        option["id"]: option["adjustment"] for option in FEATURE_OPTIONS
    }
    feature_bonus = sum(feature_adjustments.get(feat, 0) for feat in selected_features)

    land_adjustment = 0.0
    if land_size:
        comparable_land_avg = average_land(comparables)
        if comparable_land_avg:
            land_adjustment = (land_size - comparable_land_avg) * 180

    bathroom_bonus = 0
    if bathrooms is not None:
        comparable_bath_avg = mean(
            [r.bathrooms for r in comparables if r.bathrooms is not None]
        ) if comparables else None
        if comparable_bath_avg is not None and bathrooms > comparable_bath_avg:
            bathroom_bonus = (bathrooms - comparable_bath_avg) * 8000

    parking_bonus = 0
    if parking is not None:
        comparable_parking_avg = mean(
            [r.parking for r in comparables if r.parking is not None]
        ) if comparables else None
        if comparable_parking_avg is not None and parking > comparable_parking_avg:
            parking_bonus = (parking - comparable_parking_avg) * 6000

    age_adjustment = 0
    if building_age is not None:
        if building_age <= 5:
            age_adjustment = 25000
        elif building_age <= 15:
            age_adjustment = 12000
        elif building_age >= 40:
            age_adjustment = -18000
        elif building_age >= 25:
            age_adjustment = -9000

    estimate_value = (
        base_price * quality_multiplier
        + feature_bonus
        + land_adjustment
        + bathroom_bonus
        + parking_bonus
        + age_adjustment
    )
    estimate_value = max(0, estimate_value)

    breakdown = [
        {"label": "Comparable sales baseline", "value": currency(base_price)},
        {
            "label": "Quality multiplier",
            "value": f"× {quality_multiplier:.2f}",
            "description": "Average of the quality ratings selected for the property.",
        },
        {
            "label": "Feature adjustments",
            "value": currency(feature_bonus),
            "description": "Additional value based on selected amenities.",
        },
    ]

    if land_adjustment:
        breakdown.append(
            {
                "label": "Land size adjustment",
                "value": currency(land_adjustment),
                "description": "Difference compared to typical land size for similar homes.",
            }
        )
    if bathroom_bonus:
        breakdown.append(
            {
                "label": "Bathroom count adjustment",
                "value": currency(bathroom_bonus),
                "description": "Based on additional bathrooms compared to recent sales.",
            }
        )
    if parking_bonus:
        breakdown.append(
            {
                "label": "Parking adjustment",
                "value": currency(parking_bonus),
                "description": "Based on garage/car space availability.",
            }
        )
    if age_adjustment:
        breakdown.append(
            {
                "label": "Building age adjustment",
                "value": currency(age_adjustment),
                "description": "Reflects the relative age of improvements compared to newer or older stock.",
            }
        )

    return {
        "estimate": estimate_value,
        "estimate_display": currency(estimate_value),
        "breakdown": breakdown,
        "comparables": comparables,
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["PROPERTY_DATA"] = load_property_records()

    @app.context_processor
    def inject_helpers():
        return {"currency": currency}

    @app.route("/", methods=["GET", "POST"])
    def appraisal():
        records: List[PropertyRecord] = app.config["PROPERTY_DATA"]
        suburbs = sorted({record.suburb for record in records if record.suburb})

        result = None
        selected_suburb = None
        recent_sales: list[PropertyRecord] = []
        form_data = None
        quality_choices: dict[str, str] = {}
        selected_features: list[str] = []

        if request.method == "POST":
            form = request.form
            form_data = form
            selected_suburb = form.get("suburb", "").strip()
            bedrooms = parse_int(form.get("bedrooms"))
            bathrooms = parse_int(form.get("bathrooms"))
            parking = parse_int(form.get("parking"))
            land_size = parse_float(form.get("land_size"))
            building_age = parse_int(form.get("building_age"))
            quality_choices = {
                section["id"]: form.get(f"quality_{section['id']}")
                for section in QUALITY_SECTIONS
            }
            selected_features = form.getlist("features")

            result = calculate_estimate(
                all_records=records,
                suburb=selected_suburb,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                parking=parking,
                land_size=land_size,
                building_age=building_age,
                quality_choices=quality_choices,
                selected_features=selected_features,
            )

            if selected_suburb:
                recent_sales = find_recent_sales(records, selected_suburb)

        return render_template(
            "appraisal.html",
            suburbs=suburbs,
            quality_levels=QUALITY_LEVELS,
            quality_sections=QUALITY_SECTIONS,
            features=FEATURE_OPTIONS,
            result=result,
            selected_suburb=selected_suburb,
            recent_sales=recent_sales,
            form_data=form_data,
            quality_choices=quality_choices,
            selected_features=selected_features,
        )

    def normalise(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    @app.get("/api/property-info")
    def property_info():
        raw_address = request.args.get("address", "").strip()
        suburb_param = request.args.get("suburb", "").strip()
        if not raw_address:
            return jsonify({}), 400

        if "," in raw_address and not suburb_param:
            address_part, _, suburb_part = raw_address.partition(",")
            raw_address = address_part.strip()
            suburb_param = suburb_part.strip()

        address_token = normalise(raw_address)
        suburb_token = normalise(suburb_param) if suburb_param else ""

        records: List[PropertyRecord] = app.config["PROPERTY_DATA"]

        def record_matches(record: PropertyRecord) -> bool:
            if suburb_token and normalise(record.suburb) != suburb_token:
                return False
            record_address_token = normalise(record.address)
            if record_address_token == address_token:
                return True
            return address_token and address_token in record_address_token

        for record in records:
            if record_matches(record):
                return jsonify(record.serialize())

        for record in records:
            if suburb_token and normalise(record.suburb) != suburb_token:
                continue
            record_address_token = normalise(record.address)
            if address_token and record_address_token.startswith(address_token):
                return jsonify(record.serialize())

        return jsonify({}), 404

    @app.get("/api/properties")
    def property_search():
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify([])

        query_token = normalise(query)
        if not query_token:
            return jsonify([])

        records: List[PropertyRecord] = app.config["PROPERTY_DATA"]
        suggestions: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for record in records:
            tokenised_address = normalise(record.address)
            tokenised_combo = normalise(f"{record.address} {record.suburb}")
            if query_token not in tokenised_address and query_token not in tokenised_combo:
                continue
            key = (record.address, record.suburb)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append({"address": record.address, "suburb": record.suburb})
            if len(suggestions) >= 10:
                break

        return jsonify(suggestions)

    return app
