from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    interest = db.Column(db.String, nullable=False)
    intent = db.Column(db.String, nullable=True)
    payment_status = db.Column(db.String, nullable=True, default="none")
    payment_amount = db.Column(db.Integer, nullable=True)
    stripe_payment_intent_id = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Lead {self.id} {self.name}>"
