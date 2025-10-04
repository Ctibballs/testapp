from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

OFFICES = [
    "Kippax", "Kaleen", "Canberra City", "Gungahlin",
    "Tuggeranong", "Dickson", "Woden/Weston", "Country", "Projects"
]

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    initials = db.Column(db.String(8), unique=True, nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    office = db.Column(db.String(40))

    def full_name(self):
        fn = (self.first_name or '').strip()
        ln = (self.last_name or '').strip()
        return (fn + ' ' + ln).strip() or self.initials

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    address = db.Column(db.String(255), index=True)
    development = db.Column(db.String(255))
    suburb = db.Column(db.String(120), index=True)
    seen = db.Column(db.Boolean, default=False)
    price = db.Column(db.String(50))
    agent_initials = db.Column(db.String(8), index=True)
    office = db.Column(db.String(40), index=True)
    com = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(40))
    bed = db.Column(db.Integer)
    bath = db.Column(db.Integer)
    gar = db.Column(db.Integer)
    land = db.Column(db.String(80))
    access = db.Column(db.String(40))
    single_level = db.Column(db.Boolean, default=False)
    rz_zoning = db.Column(db.String(40))
    auctioneer = db.Column(db.String(120))

    description = db.Column(db.Text)
    listing_url = db.Column(db.String(500))
    needs_buyers = db.Column(db.Boolean, default=False)

    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))
    agent = db.relationship('Agent', backref='listings', lazy='joined')

class ListingImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False, index=True)
    path = db.Column(db.String(255), nullable=False)
    listing = db.relationship('Listing', backref='images', lazy='joined')
