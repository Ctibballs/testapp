from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
SUBURB_DATA_PATH = BASE_DIR / "suburb_stats.json"
LEADS_STORE_PATH = BASE_DIR / "leads.json"
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^[+\d\s()-]{6,}$")


@dataclass
class SuburbStats:
    state: str
    suburb: str
    postcode: str
    median_house_price_12m: int
    median_unit_price_12m: int
    num_house_sales_12m: int
    num_unit_sales_12m: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuburbStats":
        return cls(
            state=data["state"],
            suburb=data["suburb"],
            postcode=str(data["postcode"]),
            median_house_price_12m=int(data["median_house_price_12m"]),
            median_unit_price_12m=int(data["median_unit_price_12m"]),
            num_house_sales_12m=int(data.get("num_house_sales_12m", 0)),
            num_unit_sales_12m=int(data.get("num_unit_sales_12m", 0)),
        )

    def serialize(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "suburb": self.suburb,
            "postcode": self.postcode,
            "medianHousePrice": self.median_house_price_12m,
            "medianUnitPrice": self.median_unit_price_12m,
            "numHouseSales12m": self.num_house_sales_12m,
            "numUnitSales12m": self.num_unit_sales_12m,
        }


def load_suburb_stats() -> List[SuburbStats]:
    with SUBURB_DATA_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return [SuburbStats.from_dict(item) for item in data]


def create_app() -> Flask:
    app = Flask(__name__)
    suburb_stats = load_suburb_stats()
    leads: List[Dict[str, Any]] = []

    if LEADS_STORE_PATH.exists():
        try:
            leads_data = json.loads(LEADS_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(leads_data, list):
                leads.extend(leads_data)
        except json.JSONDecodeError:
            pass

    def persist_leads() -> None:
        LEADS_STORE_PATH.write_text(json.dumps(leads, indent=2), encoding="utf-8")

    def find_stats(suburb: str, state: str, postcode: str) -> Optional[SuburbStats]:
        target = (suburb or "").strip().lower()
        target_state = (state or "").strip().lower()
        target_postcode = (postcode or "").strip()
        for record in suburb_stats:
            if (
                record.suburb.lower() == target
                and record.state.lower() == target_state
                and record.postcode == target_postcode
            ):
                return record
        # allow postcode + state match as fallback
        for record in suburb_stats:
            if record.state.lower() == target_state and record.postcode == target_postcode:
                return record
        return None

    def derive_estimate(record: SuburbStats, payload: Dict[str, Any]) -> Dict[str, Any]:
        property_type = payload.get("propertyType", "house")
        base_price = (
            record.median_unit_price_12m if property_type == "unit" else record.median_house_price_12m
        )
        # Start with a ±5% band
        low_multiplier = 0.95
        high_multiplier = 1.05

        bedrooms = payload.get("bedrooms")
        if isinstance(bedrooms, (int, float)):
            # simple +/- 1.5% adjustment per bedroom away from 3
            low_multiplier += (bedrooms - 3) * 0.015
            high_multiplier += (bedrooms - 3) * 0.018

        land_size = payload.get("landSize")
        if isinstance(land_size, (int, float)) and property_type == "house":
            # Houses on larger blocks get a small boost, capped at ±4%
            block_adjustment = max(min((land_size - 450) / 450, 0.8), -0.8)
            low_multiplier += block_adjustment * 0.02
            high_multiplier += block_adjustment * 0.025

        estimate_low = max(int(base_price * low_multiplier), int(base_price * 0.7))
        estimate_high = int(base_price * high_multiplier)
        estimate_mid = int((estimate_low + estimate_high) / 2)

        sales_volume = (
            record.num_unit_sales_12m if property_type == "unit" else record.num_house_sales_12m
        )
        if sales_volume >= 160:
            confidence = "high"
        elif sales_volume >= 60:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "estimateLow": estimate_low,
            "estimateHigh": estimate_high,
            "estimateMid": estimate_mid,
            "confidence": confidence,
            "propertyType": property_type,
            "suburb": record.suburb,
            "state": record.state,
            "postcode": record.postcode,
            "suburbStats": record.serialize(),
        }

    @app.route("/")
    def index() -> str:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        return render_template("index.html", google_api_key=api_key)

    @app.post("/api/estimate")
    def estimate() -> Any:
        payload = request.get_json(force=True, silent=True) or {}
        required_fields = ("fullAddress", "suburb", "state", "postcode")
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            return (
                jsonify({"error": f"Missing required fields: {', '.join(missing)}"}),
                400,
            )

        record = find_stats(payload["suburb"], payload["state"], str(payload["postcode"]))
        if not record:
            # pick a safe fallback using the median of all suburbs
            fallback = suburb_stats[0]
            record = fallback

        bedrooms_value = payload.get("bedrooms")
        land_size_value = payload.get("landSize")
        if bedrooms_value is not None:
            try:
                payload["bedrooms"] = int(bedrooms_value)
            except (TypeError, ValueError):
                payload["bedrooms"] = None
        if land_size_value is not None:
            try:
                payload["landSize"] = float(land_size_value)
            except (TypeError, ValueError):
                payload["landSize"] = None

        estimate_payload = derive_estimate(record, payload)
        return jsonify(estimate_payload)

    @app.post("/api/leads")
    def create_lead() -> Any:
        payload = request.get_json(force=True, silent=True) or {}
        if not payload.get("emailEstimate") and not payload.get("connectToAgent"):
            return jsonify({"error": "At least one option must be selected."}), 400

        errors = []
        user_email = payload.get("userEmail", "").strip()
        user_phone = payload.get("userPhone", "").strip()

        if user_email and not EMAIL_REGEX.match(user_email):
            errors.append("Please provide a valid email address.")
        if user_phone and not PHONE_REGEX.match(user_phone):
            errors.append("Please provide a valid phone number.")
        if errors:
            return jsonify({"error": " ".join(errors)}), 400

        lead_entry = {
            "id": str(uuid4()),
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "fullAddress": payload.get("fullAddress"),
            "suburb": payload.get("suburb"),
            "state": payload.get("state"),
            "postcode": payload.get("postcode"),
            "propertyType": payload.get("propertyType"),
            "bedrooms": payload.get("bedrooms"),
            "landSize": payload.get("landSize"),
            "estimateLow": payload.get("estimateLow"),
            "estimateHigh": payload.get("estimateHigh"),
            "estimateMid": payload.get("estimateMid"),
            "emailEstimate": bool(payload.get("emailEstimate")),
            "connectToAgent": bool(payload.get("connectToAgent")),
            "userName": payload.get("userName"),
            "userEmail": user_email or None,
            "userPhone": user_phone or None,
        }
        leads.append(lead_entry)
        persist_leads()
        return jsonify({"status": "ok"})

    return app
