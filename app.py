import json
import os

import anthropic
from flask import Flask, flash, jsonify, redirect, render_template, request, session

from models import Lead, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ALEX_SYSTEM_PROMPT = """You are Alex, a friendly and professional assistant for [Business Name].
Your job is to have a warm, natural conversation with website visitors
to understand what they're looking for and how the business can help them.

Your personality:
- Friendly and approachable — like talking to a helpful person, not filling out a form
- Confident but never pushy — you guide the conversation without pressure
- Kind and genuinely interested in helping — you listen and respond thoughtfully
- Trustworthy — you're transparent about why you're asking for details

Your goal is to naturally collect the following information through conversation:
- Their name
- Their email address
- Their phone number
- What they're looking for and their level of interest

Rules for the conversation:
- Never ask for more than one piece of information at a time
- Never make the visitor feel interrogated — keep it conversational
- If someone seems hesitant, reassure them warmly without pressure
- Adapt your questions based on what they tell you — don't follow a rigid script
- If someone seems ready to purchase or book, acknowledge their enthusiasm warmly

When you have collected all four pieces of information, output a special
JSON summary on a new line in exactly this format and nothing else after it:

LEAD_CAPTURED::{"name":"...","email":"...","phone":"...","interest":"...","intent":"warm|hot"}

Set intent to "hot" if they expressed strong buying intent or urgency.
Set intent to "warm" if they're interested but still exploring."""

database_url = os.environ.get("DATABASE_URL", "sqlite:///leads.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat-page")
def chat_page():
    return render_template("chat.html")


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


EMPTY_MESSAGE_PLACEHOLDER = "[Start the conversation with a warm greeting]"


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or request.form
    message = data.get("message", "").strip()
    history_raw = data.get("history", [])
    history = json.loads(history_raw) if isinstance(history_raw, str) and history_raw else (history_raw or [])

    if not message:
        message = EMPTY_MESSAGE_PLACEHOLDER

    sanitized_history = [
        {**entry, "content": entry.get("content", "").strip() or EMPTY_MESSAGE_PLACEHOLDER}
        for entry in history
    ]
    messages = sanitized_history + [{"role": "user", "content": message}]

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=ALEX_SYSTEM_PROMPT,
        messages=messages,
    )
    reply_text = next((block.text for block in response.content if block.type == "text"), "")

    if "LEAD_CAPTURED::" in reply_text:
        lead_json = reply_text.split("LEAD_CAPTURED::", 1)[1].strip()
        lead_data = json.loads(lead_json)

        lead = Lead(
            name=lead_data.get("name"),
            email=lead_data.get("email"),
            phone=lead_data.get("phone"),
            interest=lead_data.get("interest"),
            intent=lead_data.get("intent"),
        )
        db.session.add(lead)
        db.session.commit()

        return jsonify({
            "lead_captured": True,
            "message": f"Thanks, {lead.name}! We've got your details and will be in touch shortly.",
        })

    return jsonify({"lead_captured": False, "message": reply_text})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
