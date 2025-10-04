from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


@dataclass
class Agent(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    initials: str = db.Column(db.String(10), unique=True, nullable=False)
    name: str = db.Column(db.String(120), nullable=False)
    email: str = db.Column(db.String(120), nullable=True)
    phone: str = db.Column(db.String(40), nullable=True)
    office: str = db.Column(db.String(40), nullable=False)

    listings = db.relationship("Listing", back_populates="agent", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - simple repr helper
        return f"<Agent {self.initials}>"


@dataclass
class Listing(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    date: Optional[datetime] = db.Column(db.Date, nullable=True)
    time: Optional[str] = db.Column(db.String(50), nullable=True)
    address: str = db.Column(db.String(255), nullable=False)
    development: Optional[str] = db.Column(db.String(255), nullable=True)
    suburb: Optional[str] = db.Column(db.String(100), nullable=True)
    seen: Optional[str] = db.Column(db.String(20), nullable=True)
    price: Optional[str] = db.Column(db.String(120), nullable=True)
    agent_initials: Optional[str] = db.Column(db.String(10), nullable=True)
    office: Optional[str] = db.Column(db.String(40), nullable=True)
    compliant: Optional[str] = db.Column(db.String(10), nullable=True)
    property_type: Optional[str] = db.Column(db.String(120), nullable=True)
    bed: Optional[str] = db.Column(db.String(20), nullable=True)
    bath: Optional[str] = db.Column(db.String(20), nullable=True)
    gar: Optional[str] = db.Column(db.String(20), nullable=True)
    land: Optional[str] = db.Column(db.String(50), nullable=True)
    access: Optional[str] = db.Column(db.String(50), nullable=True)
    single_level: Optional[str] = db.Column(db.String(20), nullable=True)
    rz_zoning: Optional[str] = db.Column(db.String(50), nullable=True)
    auctioneer: Optional[str] = db.Column(db.String(120), nullable=True)
    description: Optional[str] = db.Column(db.Text, nullable=True)
    listing_link: Optional[str] = db.Column(db.String(255), nullable=True)
    needs_help: bool = db.Column(db.Boolean, default=False)

    agent_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("agent.id"), nullable=True)
    agent = db.relationship("Agent", back_populates="listings", lazy=True)

    images = db.relationship(
        "ListingImage",
        back_populates="listing",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="ListingImage.id",
    )

    def __repr__(self) -> str:  # pragma: no cover - simple repr helper
        return f"<Listing {self.address}>"


@dataclass
class ListingImage(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    filename: str = db.Column(db.String(255), nullable=False)
    listing_id: int = db.Column(db.Integer, db.ForeignKey("listing.id"), nullable=False)

    listing = db.relationship("Listing", back_populates="images", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - simple repr helper
        return f"<ListingImage {self.filename}>"
