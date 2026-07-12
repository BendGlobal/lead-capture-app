import os
import re
from urllib.parse import quote

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")


def _slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "business"


def _from_email():
    from_email = os.environ.get("SENDGRID_FROM_EMAIL")
    from_name = os.environ.get("SENDGRID_FROM_NAME", "")
    if not from_email:
        raise RuntimeError("SENDGRID_FROM_EMAIL environment variable is not set")
    return (from_email, from_name) if from_name else from_email


def _get_client():
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY environment variable is not set")
    return SendGridAPIClient(api_key)


def send_lead_confirmation(lead, business_name, services, location):
    first_name = (lead.name or "there").split()[0]
    slug = _slugify(business_name)
    intro_url = (
        f"{APP_BASE_URL}/business/{slug}"
        f"?name={quote(lead.name or '')}"
        f"&business={quote(business_name or '')}"
        f"&services={quote(services or '')}"
        f"&location={quote(location or '')}"
    )

    html_content = f"""
    <html>
      <body style="margin:0; padding:0; background:#f4f6f8; font-family:'Segoe UI', Helvetica, Arial, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8; padding:40px 20px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" style="max-width:520px; background:#ffffff; border-radius:10px; overflow:hidden;">
                <tr>
                  <td style="padding:36px 36px 24px;">
                    <h1 style="margin:0 0 12px; font-size:22px; color:#16213e;">Thanks for reaching out, {first_name}!</h1>
                    <p style="margin:0 0 20px; font-size:15px; line-height:1.6; color:#334155;">
                      We've received your enquiry with <strong>{business_name}</strong> and someone from
                      the team will be in touch with you shortly.
                    </p>
                    <p style="margin:0 0 28px; font-size:15px; line-height:1.6; color:#334155;">
                      In the meantime, take a look at our services and get a feel for who you'll be working with.
                    </p>
                    <table role="presentation" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="border-radius:6px; background:#2f6feb;">
                          <a href="{intro_url}" target="_blank"
                             style="display:inline-block; padding:14px 28px; font-size:15px; font-weight:600;
                                    color:#ffffff; text-decoration:none;">
                            Learn more about {business_name}
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 36px 32px; border-top:1px solid #e4e9f0;">
                    <p style="margin:0; font-size:13px; color:#8b98a8;">
                      This email was sent because you submitted an enquiry with {business_name}.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message = Mail(
        from_email=_from_email(),
        to_emails=lead.email,
        subject=f"Thanks for reaching out to {business_name}!",
        html_content=html_content,
    )
    client = _get_client()
    return client.send(message)


def send_owner_notification(lead, business_name, owner_email):
    if not owner_email:
        raise RuntimeError("owner_email is required to send the owner notification")

    dashboard_url = f"{APP_BASE_URL}/leads"
    intent_display = lead.intent or "Not specified"

    html_content = f"""
    <html>
      <body style="margin:0; padding:0; background:#f4f6f8; font-family:'Segoe UI', Helvetica, Arial, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8; padding:40px 20px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" style="max-width:520px; background:#ffffff; border-radius:10px; overflow:hidden;">
                <tr>
                  <td style="padding:32px 32px 8px;">
                    <h1 style="margin:0 0 4px; font-size:20px; color:#16213e;">New lead for {business_name}</h1>
                    <p style="margin:0 0 24px; font-size:14px; color:#616e7c;">
                      A new lead just came in through your chat widget.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 32px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px; color:#1f2933;">
                      <tr>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0; font-weight:600; width:110px;">Name</td>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0;">{lead.name}</td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0; font-weight:600;">Email</td>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0;">{lead.email}</td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0; font-weight:600;">Phone</td>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0;">{lead.phone}</td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0; font-weight:600;">Interest</td>
                        <td style="padding:8px 0; border-bottom:1px solid #e4e9f0;">{lead.interest}</td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0; font-weight:600;">Intent</td>
                        <td style="padding:8px 0;">{intent_display}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:28px 32px 8px;">
                    <p style="margin:0 0 20px; font-size:15px; font-weight:600; color:#b91c1c;">
                      Call {lead.name} now at <a href="tel:{lead.phone}" style="color:#b91c1c;">{lead.phone}</a> while the lead is fresh.
                    </p>
                    <table role="presentation" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="border-radius:6px; background:#16213e;">
                          <a href="{dashboard_url}" target="_blank"
                             style="display:inline-block; padding:12px 22px; font-size:14px; font-weight:600;
                                    color:#ffffff; text-decoration:none;">
                            View Lead Dashboard
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 32px 32px;">&nbsp;</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message = Mail(
        from_email=_from_email(),
        to_emails=owner_email,
        subject=f"New lead from {business_name}: {lead.name}",
        html_content=html_content,
    )
    client = _get_client()
    return client.send(message)


def send_payment_confirmation(lead, amount_cents):
    first_name = (lead.name or "there").split()[0]
    amount_display = f"${amount_cents / 100:,.2f}"

    html_content = f"""
    <html>
      <body style="margin:0; padding:0; background:#f4f6f8; font-family:'Segoe UI', Helvetica, Arial, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8; padding:40px 20px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" style="max-width:520px; background:#ffffff; border-radius:10px; overflow:hidden;">
                <tr>
                  <td style="padding:36px 36px 24px;">
                    <h1 style="margin:0 0 12px; font-size:22px; color:#16213e;">Your booking is confirmed, {first_name}!</h1>
                    <p style="margin:0 0 20px; font-size:15px; line-height:1.6; color:#334155;">
                      We've received your deposit of <strong>{amount_display}</strong>. Your booking is confirmed.
                    </p>
                    <p style="margin:0; font-size:15px; line-height:1.6; color:#334155;">
                      Someone will be in touch shortly to confirm the details.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message = Mail(
        from_email=_from_email(),
        to_emails=lead.email,
        subject="Your booking is confirmed!",
        html_content=html_content,
    )
    client = _get_client()
    return client.send(message)
