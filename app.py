import os

from flask import Flask, flash, redirect, render_template, request, session

from models import Lead, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///leads.db"

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    interest = request.form.get("interest", "").strip()

    if not all([name, email, phone, interest]):
        flash("Please fill in all fields")
        return redirect("/")

    lead = Lead(name=name, email=email, phone=phone, interest=interest)
    db.session.add(lead)
    db.session.commit()
    session["last_lead"] = {
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "interest": lead.interest,
        "created_at": lead.created_at.strftime("%b %d, %Y %I:%M %p UTC"),
    }
    return redirect("/thanks")


@app.route("/thanks")
def thanks():
    lead = session.pop("last_lead", None)
    return render_template("thanks.html", lead=lead)


@app.route("/leads")
def leads():
    all_leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template("leads.html", leads=all_leads)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
