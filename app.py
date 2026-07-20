import json
import os

import anthropic
import stripe
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_cors import CORS

from email_service import send_lead_confirmation, send_owner_notification, send_payment_confirmation
from models import Lead, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")

CORS(app, resources={r"/chat": {"origins": "*"}, r"/create-payment-intent": {"origins": "*"}})

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

ALEX_SYSTEM_PROMPT = """You are Alex, a friendly and professional assistant for {business_name}.
{business_name} offers the following services: {services}. It is located in {location}.
Your job is to have a warm, natural conversation with website visitors
to understand what they're looking for and how the business can help them.

Communication style: {tone}

If tone is "direct":
- Maximum 2 sentences per response
- No emojis unless the visitor uses them first
- No enthusiasm phrases like "Great!", "Fantastic!", "Love it!", "That's awesome!"
- Ask one question only, never two at once
- Never restate what the visitor just told you back to them
- Get to the point immediately

If tone is "warm":
- Maximum 3 sentences per response
- Maximum 1 emoji per message
- Genuine warmth through word choice, not length
- Still concise and efficient
- One question per message only

If tone is "formal":
- Complete sentences, proper grammar throughout
- No emojis under any circumstances
- No exclamation marks
- Professional and measured language
- Address the visitor respectfully and precisely

If tone is "friendly":
- Maximum 3 sentences per response
- Maximum 2 emojis per message
- Upbeat but not over the top
- Natural conversational rhythm
- One question per message

If tone is "luxury":
- Short, confident, understated responses
- No emojis, no exclamation marks
- Sophisticated word choice
- Never pushy or enthusiastic
- Let the visitor lead the pace

Emoji usage override: {emoji_style}
If emoji_style is "none" — never use emojis regardless of tone
If emoji_style is "minimal" — maximum 1 emoji per response regardless of tone
If emoji_style is "normal" — follow the tone guidelines above

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

Once you have collected all four pieces of information, determine their intent:
set intent to "hot" if they expressed strong buying intent or urgency, or "warm"
if they're interested but still exploring.

If {payment_enabled} is true and the visitor has expressed strong buying intent,
after collecting all four details naturally introduce the payment option using
this exact framing: "{offer_headline}. {incentive_text}. I can lock in your
{priority_label} right now with a {payment_label} of {payment_amount} — that way
you're guaranteed to be first in the queue. Would you like to secure that now, or
would you prefer we just give you a call back?"

If they agree, output a special JSON summary on a new line in exactly this format
and nothing else after it:

PAYMENT_READY::{{"name":"...","email":"...","phone":"...","interest":"...","intent":"hot"}}

If they decline, or if {payment_enabled} is false, or their intent is "warm" rather
than "hot", output a special JSON summary on a new line in exactly this format and
nothing else after it:

LEAD_CAPTURED::{{"name":"...","email":"...","phone":"...","interest":"...","intent":"warm|hot"}}"""

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
DEFAULT_BUSINESS_NAME = "our business"
DEFAULT_SERVICES = "a range of products and services"
DEFAULT_LOCATION = "our local area"
DEFAULT_PAYMENT_ENABLED = "true"
DEFAULT_PAYMENT_LABEL = "deposit"
DEFAULT_PAYMENT_AMOUNT = "$100"
DEFAULT_PRIORITY_LABEL = "priority booking"
DEFAULT_OFFER_HEADLINE = "Secure your booking now!"
DEFAULT_INCENTIVE = "Pay your deposit now and we'll prioritise your job"
DEFAULT_TONE = "friendly"
DEFAULT_EMOJI_STYLE = "normal"


@app.route("/business/<slug>")
def business_page(slug):
    lead_name = request.args.get("name", "").strip() or "there"
    services = request.args.get("services", "").strip() or DEFAULT_SERVICES
    location = request.args.get("location", "").strip() or DEFAULT_LOCATION
    business_name = (
        request.args.get("business", "").strip()
        or slug.replace("-", " ").strip().title()
        or DEFAULT_BUSINESS_NAME
    )

    return render_template(
        "business.html",
        business_name=business_name,
        lead_name=lead_name,
        services=services,
        location=location,
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or request.form
    message = data.get("message", "").strip()
    history_raw = data.get("history", [])
    history = json.loads(history_raw) if isinstance(history_raw, str) and history_raw else (history_raw or [])

    business_name = data.get("business_name", "").strip() or DEFAULT_BUSINESS_NAME
    services = data.get("services", "").strip() or DEFAULT_SERVICES
    location = data.get("location", "").strip() or DEFAULT_LOCATION

    payment_enabled = (data.get("payment_enabled") or DEFAULT_PAYMENT_ENABLED).strip().lower()
    if payment_enabled not in ("true", "false"):
        payment_enabled = DEFAULT_PAYMENT_ENABLED
    payment_label = data.get("payment_label", "").strip() or DEFAULT_PAYMENT_LABEL
    payment_amount = data.get("payment_amount", "").strip() or DEFAULT_PAYMENT_AMOUNT
    priority_label = data.get("priority_label", "").strip() or DEFAULT_PRIORITY_LABEL
    offer_headline = (data.get("offer_headline", "").strip() or DEFAULT_OFFER_HEADLINE).rstrip(".!?")
    incentive_text = (data.get("incentive", "").strip() or DEFAULT_INCENTIVE).rstrip(".!?")
    tone = data.get("tone", "").strip() or DEFAULT_TONE
    emoji_style = data.get("emoji_style", "").strip() or DEFAULT_EMOJI_STYLE

    system_prompt = ALEX_SYSTEM_PROMPT.format(
        business_name=business_name,
        services=services,
        location=location,
        payment_enabled=payment_enabled,
        payment_label=payment_label,
        payment_amount=payment_amount,
        priority_label=priority_label,
        offer_headline=offer_headline,
        incentive_text=incentive_text,
        tone=tone,
        emoji_style=emoji_style,
    )

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
        system=system_prompt,
        messages=messages,
    )
    reply_text = next((block.text for block in response.content if block.type == "text"), "")

    marker = None
    if "PAYMENT_READY::" in reply_text:
        marker = "PAYMENT_READY::"
    elif "LEAD_CAPTURED::" in reply_text:
        marker = "LEAD_CAPTURED::"

    if marker:
        lead_json = reply_text.split(marker, 1)[1].strip()
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

        try:
            send_lead_confirmation(lead, business_name, services, location)
        except Exception:
            app.logger.exception("Failed to send lead confirmation email")

        try:
            owner_email = os.environ.get("OWNER_EMAIL")
            send_owner_notification(lead, business_name, owner_email)
        except Exception:
            app.logger.exception("Failed to send owner notification email")

        if marker == "PAYMENT_READY::":
            return jsonify({
                "lead_captured": True,
                "payment_ready": True,
                "lead_id": lead.id,
                "intent": lead.intent,
                "message": f"Perfect, {lead.name}! Let's get your {payment_label} sorted so we can lock in your {priority_label}.",
            })

        return jsonify({
            "lead_captured": True,
            "message": f"Thanks, {lead.name}! We've got your details and will be in touch shortly.",
            "lead_id": lead.id,
            "intent": lead.intent,
            "payment_offered": payment_enabled == "true" and lead.intent == "hot",
        })

    return jsonify({"lead_captured": False, "message": reply_text})


@app.route("/create-payment-intent", methods=["POST"])
def create_payment_intent():
    data = request.get_json(silent=True) or {}
    lead_id = data.get("lead_id")
    amount = data.get("amount", 10000)
    currency = (data.get("currency") or "aud").strip().lower()
    payment_label = data.get("payment_label", "").strip() or DEFAULT_PAYMENT_LABEL
    priority_label = data.get("priority_label", "").strip() or DEFAULT_PRIORITY_LABEL

    lead = db.session.get(Lead, lead_id)
    if lead is None:
        return jsonify({"error": "Lead not found"}), 404

    payment_intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        metadata={
            "lead_id": str(lead.id),
            "payment_label": payment_label,
            "priority_label": priority_label,
        },
    )

    lead.stripe_payment_intent_id = payment_intent.id
    lead.payment_status = "pending"
    db.session.commit()

    return jsonify({
        "client_secret": payment_intent.client_secret,
        "payment_intent_id": payment_intent.id,
    })


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return "Invalid signature", 400

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        lead = Lead.query.filter_by(stripe_payment_intent_id=payment_intent["id"]).first()

        if lead is not None:
            lead.payment_status = "completed"
            lead.payment_amount = payment_intent["amount_received"]
            db.session.commit()

            metadata = payment_intent.metadata or {}
            payment_label = getattr(payment_intent.metadata, "payment_label", "deposit")
            priority_label = getattr(payment_intent.metadata, "priority_label", "priority booking")

            try:
                send_payment_confirmation(lead, lead.payment_amount, payment_label, priority_label)
            except Exception:
                app.logger.exception("Failed to send payment confirmation email")

    return "", 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
