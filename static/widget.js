(function () {
  "use strict";

  var scriptTag = document.currentScript;
  if (!scriptTag) {
    var scripts = document.getElementsByTagName("script");
    scriptTag = scripts[scripts.length - 1];
  }

  var config = {
    businessName: scriptTag.getAttribute("data-business") || "our business",
    services: scriptTag.getAttribute("data-services") || "a range of products and services",
    location: scriptTag.getAttribute("data-location") || "our local area",
    mode: scriptTag.getAttribute("data-mode") || "bubble",
    apiUrl: scriptTag.getAttribute("data-api-url") || "",
    stripePublishableKey: scriptTag.getAttribute("data-stripe-publishable-key") || "",
    depositAmount: parseFloat(scriptTag.getAttribute("data-deposit-amount")) || 100,
    offerHeadline: scriptTag.getAttribute("data-offer-headline") || "Secure your booking now!",
    incentive: scriptTag.getAttribute("data-incentive") || "Pay your deposit now and we'll prioritise your job",
    countdownMinutes: parseFloat(scriptTag.getAttribute("data-countdown")) || 15,
  };

  if (!config.apiUrl) {
    console.error(
      "[Alex Widget] Missing required data-api-url attribute on the widget's <script> tag. " +
      "The widget doesn't know where your server lives, so it can't send chat requests. " +
      'Add data-api-url="https://your-app.onrender.com" to the script tag.'
    );
    return;
  }

  var CHAT_ENDPOINT = config.apiUrl.replace(/\/+$/, "") + "/chat";
  var PAYMENT_INTENT_ENDPOINT = config.apiUrl.replace(/\/+$/, "") + "/create-payment-intent";
  var STRIPE_JS_URL = "https://js.stripe.com/v3/";
  var MODAL_STYLE_ID = "aw-payment-modal-styles";

  // Stripe Elements does not render reliably inside a Shadow DOM (iframe sizing
  // and postMessage issues), so the payment modal lives directly on document.body,
  // outside the widget's shadow root. Because it's unprotected by shadow isolation,
  // the critical visual properties are set !important so they survive aggressive
  // host-page CSS (e.g. `* { color: red !important }`).
  var MODAL_CSS = "" +
    ".aw-payment-modal-overlay {" +
    "  all: initial;" +
    "  position: fixed;" +
    "  top: 0; left: 0; right: 0; bottom: 0;" +
    "  background: rgba(15, 23, 42, 0.55);" +
    "  display: flex;" +
    "  align-items: center;" +
    "  justify-content: center;" +
    "  z-index: 2147483647;" +
    "  padding: 20px;" +
    "  box-sizing: border-box;" +
    "}" +
    ".aw-payment-modal-overlay, .aw-payment-modal-overlay * {" +
    "  box-sizing: border-box;" +
    "  font-family: 'Segoe UI', Helvetica, Arial, sans-serif !important;" +
    "}" +
    ".aw-payment-modal-box {" +
    "  background: #ffffff !important;" +
    "  border-radius: 14px !important;" +
    "  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);" +
    "  width: 100%;" +
    "  max-width: 380px;" +
    "  padding: 20px;" +
    "  color: #1f2933 !important;" +
    "}" +
    ".aw-payment-modal-header {" +
    "  display: flex;" +
    "  align-items: center;" +
    "  justify-content: space-between;" +
    "  margin-bottom: 14px;" +
    "}" +
    ".aw-payment-modal-header span {" +
    "  font-size: 15px;" +
    "  font-weight: 700;" +
    "  color: #16213e !important;" +
    "}" +
    ".aw-payment-modal-close {" +
    "  background: transparent !important;" +
    "  border: none !important;" +
    "  color: #616e7c !important;" +
    "  font-size: 22px;" +
    "  line-height: 1;" +
    "  cursor: pointer;" +
    "  padding: 0 !important;" +
    "}" +
    ".aw-payment-modal-mount {" +
    "  min-height: 180px;" +
    "  margin-bottom: 14px;" +
    "}" +
    ".aw-payment-modal-loading {" +
    "  font-size: 13px;" +
    "  color: #616e7c !important;" +
    "  text-align: center;" +
    "  padding: 24px 0;" +
    "}" +
    ".aw-payment-modal-submit-btn {" +
    "  width: 100%;" +
    "  padding: 11px 14px !important;" +
    "  font-size: 14px;" +
    "  font-weight: 600;" +
    "  color: #ffffff !important;" +
    "  background: #2f6feb !important;" +
    "  border: none !important;" +
    "  border-radius: 6px !important;" +
    "  cursor: pointer;" +
    "}" +
    ".aw-payment-modal-submit-btn:hover {" +
    "  background: #2657c4 !important;" +
    "}" +
    ".aw-payment-modal-submit-btn:disabled {" +
    "  opacity: 0.6;" +
    "  cursor: not-allowed;" +
    "}" +
    ".aw-payment-modal-status {" +
    "  font-size: 12.5px;" +
    "  margin-top: 8px;" +
    "}" +
    ".aw-payment-modal-success {" +
    "  text-align: center;" +
    "  padding: 20px 0;" +
    "  font-size: 14px;" +
    "  color: #16a34a !important;" +
    "  font-weight: 600;" +
    "}";

  var WIDGET_CSS = "" +
    ":host {" +
    "  all: initial;" +
    "  position: fixed;" +
    "  bottom: 24px;" +
    "  right: 24px;" +
    "  z-index: 2147483647;" +
    "  display: block;" +
    "}" +
    ".widget-root, .widget-root * {" +
    "  box-sizing: border-box;" +
    "  font-family: 'Segoe UI', Helvetica, Arial, sans-serif;" +
    "}" +
    ".widget-root {" +
    "  position: relative;" +
    "}" +
    ".bubble {" +
    "  width: 56px;" +
    "  height: 56px;" +
    "  border-radius: 50%;" +
    "  background: #2f6feb;" +
    "  border: none;" +
    "  cursor: pointer;" +
    "  display: flex;" +
    "  align-items: center;" +
    "  justify-content: center;" +
    "  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);" +
    "  color: #fff;" +
    "  padding: 0;" +
    "}" +
    ".bubble:hover {" +
    "  background: #2657c4;" +
    "}" +
    ".bubble svg {" +
    "  width: 26px;" +
    "  height: 26px;" +
    "}" +
    ".panel {" +
    "  position: absolute;" +
    "  bottom: 72px;" +
    "  right: 0;" +
    "  width: 340px;" +
    "  max-width: calc(100vw - 48px);" +
    "  height: 460px;" +
    "  max-height: calc(100vh - 140px);" +
    "  background: #fff;" +
    "  border-radius: 14px;" +
    "  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);" +
    "  display: flex;" +
    "  flex-direction: column;" +
    "  overflow: hidden;" +
    "  opacity: 0;" +
    "  transform: translateY(12px) scale(0.98);" +
    "  pointer-events: none;" +
    "  transition: opacity 0.15s ease, transform 0.15s ease;" +
    "}" +
    ".panel.open {" +
    "  opacity: 1;" +
    "  transform: translateY(0) scale(1);" +
    "  pointer-events: auto;" +
    "}" +
    ".panel-header {" +
    "  background: #16213e;" +
    "  color: #fff;" +
    "  padding: 14px 16px;" +
    "  font-size: 15px;" +
    "  font-weight: 600;" +
    "  display: flex;" +
    "  align-items: center;" +
    "  justify-content: space-between;" +
    "  flex-shrink: 0;" +
    "}" +
    ".close-btn {" +
    "  background: transparent;" +
    "  border: none;" +
    "  color: #fff;" +
    "  font-size: 20px;" +
    "  line-height: 1;" +
    "  cursor: pointer;" +
    "  padding: 0;" +
    "}" +
    ".messages {" +
    "  flex: 1;" +
    "  overflow-y: auto;" +
    "  padding: 14px;" +
    "  display: flex;" +
    "  flex-direction: column;" +
    "  gap: 10px;" +
    "  background: #fff;" +
    "}" +
    ".message {" +
    "  max-width: 78%;" +
    "  padding: 9px 12px;" +
    "  border-radius: 13px;" +
    "  font-size: 13.5px;" +
    "  line-height: 1.45;" +
    "  white-space: pre-wrap;" +
    "  word-wrap: break-word;" +
    "  color: #1f2933;" +
    "}" +
    ".message.alex {" +
    "  align-self: flex-start;" +
    "  background: #f1f4f9;" +
    "  color: #1f2933;" +
    "  border-bottom-left-radius: 4px;" +
    "}" +
    ".message.visitor {" +
    "  align-self: flex-end;" +
    "  background: #2f6feb;" +
    "  color: #fff;" +
    "  border-bottom-right-radius: 4px;" +
    "}" +
    ".message.system-note {" +
    "  align-self: center;" +
    "  background: transparent;" +
    "  color: #8b98a8;" +
    "  font-size: 12px;" +
    "  font-style: italic;" +
    "  text-align: center;" +
    "  max-width: 100%;" +
    "}" +
    ".typing-indicator {" +
    "  display: none;" +
    "  align-self: flex-start;" +
    "  font-size: 12px;" +
    "  color: #8b98a8;" +
    "  font-style: italic;" +
    "  padding: 0 14px 6px;" +
    "  margin: 0;" +
    "}" +
    ".typing-indicator.visible {" +
    "  display: block;" +
    "}" +
    ".input-row {" +
    "  display: flex;" +
    "  gap: 8px;" +
    "  border-top: 1px solid #e4e9f0;" +
    "  padding: 12px;" +
    "  flex-shrink: 0;" +
    "  background: #fff;" +
    "}" +
    ".chat-input {" +
    "  flex: 1;" +
    "  padding: 9px 11px;" +
    "  font-size: 13.5px;" +
    "  border: 1px solid #cbd2d9;" +
    "  border-radius: 6px;" +
    "  color: #1f2933;" +
    "  background: #fff;" +
    "  outline: none;" +
    "}" +
    ".chat-input:focus {" +
    "  border-color: #3b82f6;" +
    "  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);" +
    "}" +
    ".send-btn {" +
    "  padding: 9px 16px;" +
    "  font-size: 13.5px;" +
    "  font-weight: 600;" +
    "  color: #fff;" +
    "  background: #2f6feb;" +
    "  border: none;" +
    "  border-radius: 6px;" +
    "  cursor: pointer;" +
    "  flex-shrink: 0;" +
    "}" +
    ".send-btn:hover {" +
    "  background: #2657c4;" +
    "}" +
    ".chat-input:disabled, .send-btn:disabled {" +
    "  opacity: 0.6;" +
    "  cursor: not-allowed;" +
    "}" +
    ".payment-offer {" +
    "  align-self: stretch;" +
    "  max-width: 100%;" +
    "  background: #fff8ec;" +
    "  border: 1px solid #f3d9a4;" +
    "  border-radius: 12px;" +
    "  padding: 14px;" +
    "  display: flex;" +
    "  flex-direction: column;" +
    "  gap: 8px;" +
    "}" +
    ".payment-offer .offer-headline {" +
    "  font-size: 14.5px;" +
    "  font-weight: 700;" +
    "  color: #16213e;" +
    "}" +
    ".payment-offer .offer-incentive {" +
    "  font-size: 13px;" +
    "  color: #616e7c;" +
    "  line-height: 1.4;" +
    "}" +
    ".payment-offer .offer-deposit {" +
    "  font-size: 13.5px;" +
    "  color: #1f2933;" +
    "}" +
    ".payment-offer .offer-deposit strong {" +
    "  color: #16213e;" +
    "  font-size: 16px;" +
    "}" +
    ".payment-offer .offer-countdown {" +
    "  font-size: 12px;" +
    "  color: #b45309;" +
    "  font-weight: 600;" +
    "}" +
    ".payment-offer .offer-actions {" +
    "  display: flex;" +
    "  gap: 8px;" +
    "  margin-top: 4px;" +
    "}" +
    ".pay-now-btn {" +
    "  flex: 1;" +
    "  padding: 10px 14px;" +
    "  font-size: 13.5px;" +
    "  font-weight: 600;" +
    "  color: #fff;" +
    "  background: #16a34a;" +
    "  border: none;" +
    "  border-radius: 6px;" +
    "  cursor: pointer;" +
    "}" +
    ".pay-now-btn:hover {" +
    "  background: #15803d;" +
    "}" +
    ".pay-now-btn:disabled {" +
    "  opacity: 0.6;" +
    "  cursor: not-allowed;" +
    "}" +
    ".dismiss-btn {" +
    "  padding: 10px 12px;" +
    "  font-size: 13px;" +
    "  font-weight: 600;" +
    "  color: #616e7c;" +
    "  background: transparent;" +
    "  border: 1px solid #cbd2d9;" +
    "  border-radius: 6px;" +
    "  cursor: pointer;" +
    "}" +
    ".payment-status-msg {" +
    "  font-size: 12.5px;" +
    "  color: #b91c1c;" +
    "  margin-top: 4px;" +
    "}" +
    ".payment-offer.expired .pay-now-btn {" +
    "  opacity: 0.5;" +
    "  cursor: not-allowed;" +
    "}" +
    ".payment-offer.success {" +
    "  background: #f0fdf4;" +
    "  border-color: #86efac;" +
    "}";

  var WIDGET_HTML = "" +
    '<button class="bubble" type="button" aria-label="Open chat" aria-expanded="false">' +
    '  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">' +
    '    <path d="M4 4h16v12H7l-3 3V4z" fill="currentColor"/>' +
    "  </svg>" +
    "</button>" +
    '<div class="panel">' +
    '  <div class="panel-header">' +
    "    <span>Chat with Alex</span>" +
    '    <button type="button" class="close-btn" aria-label="Close chat">&times;</button>' +
    "  </div>" +
    '  <div class="messages"></div>' +
    '  <p class="typing-indicator">Alex is typing...</p>' +
    '  <div class="input-row">' +
    '    <input type="text" class="chat-input" placeholder="Type your message..." autocomplete="off">' +
    '    <button type="button" class="send-btn">Send</button>' +
    "  </div>" +
    "</div>";

  function init() {
    if (config.mode !== "bubble") {
      console.warn('[Alex Widget] data-mode="' + config.mode + '" is not implemented yet; falling back to bubble mode.');
    }

    var host = document.createElement("div");
    host.id = "alex-chat-widget";
    document.body.appendChild(host);

    var shadow = host.attachShadow({ mode: "open" });

    var styleEl = document.createElement("style");
    styleEl.textContent = WIDGET_CSS;
    shadow.appendChild(styleEl);

    var root = document.createElement("div");
    root.className = "widget-root";
    root.innerHTML = WIDGET_HTML;
    shadow.appendChild(root);

    var bubble = root.querySelector(".bubble");
    var panel = root.querySelector(".panel");
    var closeBtn = root.querySelector(".close-btn");
    var messagesEl = root.querySelector(".messages");
    var typingEl = root.querySelector(".typing-indicator");
    var inputEl = root.querySelector(".chat-input");
    var sendBtn = root.querySelector(".send-btn");

    var conversationHistory = [];
    var leadCaptured = false;
    var panelOpened = false;
    var currentLeadId = null;
    var stripeJsPromise = null;

    function appendMessage(role, text) {
      var div = document.createElement("div");
      div.className = "message " + (role === "user" ? "visitor" : "alex");
      div.textContent = text;
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function appendSystemNote(text) {
      var div = document.createElement("div");
      div.className = "message system-note";
      div.textContent = text;
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function setInputEnabled(enabled) {
      inputEl.disabled = !enabled;
      sendBtn.disabled = !enabled;
    }

    function loadStripeJs() {
      if (window.Stripe) {
        return Promise.resolve(window.Stripe);
      }
      if (stripeJsPromise) {
        return stripeJsPromise;
      }
      stripeJsPromise = new Promise(function (resolve, reject) {
        var existing = document.querySelector('script[src="' + STRIPE_JS_URL + '"]');
        if (existing) {
          existing.addEventListener("load", function () {
            resolve(window.Stripe);
          });
          existing.addEventListener("error", reject);
          return;
        }
        var script = document.createElement("script");
        script.src = STRIPE_JS_URL;
        script.async = true;
        script.onload = function () {
          resolve(window.Stripe);
        };
        script.onerror = function () {
          reject(new Error("Failed to load Stripe.js"));
        };
        document.head.appendChild(script);
      });
      return stripeJsPromise;
    }

    function formatDollars(amount) {
      return "$" + Number(amount).toFixed(2).replace(/\.00$/, "");
    }

    function injectModalStyles() {
      if (document.getElementById(MODAL_STYLE_ID)) return;
      var styleEl = document.createElement("style");
      styleEl.id = MODAL_STYLE_ID;
      styleEl.textContent = MODAL_CSS;
      document.head.appendChild(styleEl);
    }

    // Mounts the Stripe Payment Element in a modal attached to document.body,
    // outside the shadow root — Stripe Elements does not render reliably inside
    // a Shadow DOM. onSuccess/onCancel let the caller update the payment-offer
    // card once the modal closes.
    function openPaymentModal(clientSecret, onSuccess, onCancel) {
      injectModalStyles();

      var overlay = document.createElement("div");
      overlay.className = "aw-payment-modal-overlay";
      overlay.innerHTML =
        '<div class="aw-payment-modal-box">' +
        '  <div class="aw-payment-modal-header">' +
        "    <span>Complete Your Payment</span>" +
        '    <button type="button" class="aw-payment-modal-close" aria-label="Close">&times;</button>' +
        "  </div>" +
        '  <div class="aw-payment-modal-mount">' +
        '    <div class="aw-payment-modal-loading">Loading secure payment form...</div>' +
        "  </div>" +
        '  <button type="button" class="aw-payment-modal-submit-btn" style="display:none;">Submit Payment</button>' +
        '  <div class="aw-payment-modal-status"></div>' +
        "</div>";

      document.body.appendChild(overlay);

      var mountEl = overlay.querySelector(".aw-payment-modal-mount");
      var submitBtn = overlay.querySelector(".aw-payment-modal-submit-btn");
      var statusEl = overlay.querySelector(".aw-payment-modal-status");
      var closeBtn = overlay.querySelector(".aw-payment-modal-close");
      var closed = false;

      function closeModal() {
        if (closed) return;
        closed = true;
        overlay.remove();
      }

      closeBtn.addEventListener("click", function () {
        closeModal();
        if (onCancel) onCancel();
      });

      loadStripeJs()
        .then(function (Stripe) {
          if (closed) return;
          var stripe = Stripe(config.stripePublishableKey);
          var elements = stripe.elements({ clientSecret: clientSecret });
          var paymentElement = elements.create("payment");

          mountEl.innerHTML = "";
          paymentElement.mount(mountEl);
          submitBtn.style.display = "block";

          submitBtn.addEventListener("click", function () {
            submitBtn.disabled = true;
            statusEl.style.setProperty("color", "#616e7c", "important");
            statusEl.textContent = "Processing payment...";

            stripe
              .confirmPayment({ elements: elements, redirect: "if_required" })
              .then(function (result) {
                if (result.error) {
                  statusEl.style.setProperty("color", "#b91c1c", "important");
                  statusEl.textContent = result.error.message || "Payment failed. Please try again.";
                  submitBtn.disabled = false;
                  return;
                }
                overlay.querySelector(".aw-payment-modal-box").innerHTML =
                  '<div class="aw-payment-modal-success">Payment successful!</div>';
                setTimeout(function () {
                  closeModal();
                  if (onSuccess) onSuccess();
                }, 1500);
              })
              .catch(function () {
                statusEl.style.setProperty("color", "#b91c1c", "important");
                statusEl.textContent = "Something went wrong processing your payment. Please try again.";
                submitBtn.disabled = false;
              });
          });
        })
        .catch(function () {
          if (closed) return;
          mountEl.innerHTML = '<div class="aw-payment-modal-loading">Could not load the payment form. Please try again.</div>';
        });
    }

    function showPaymentOffer() {
      var card = document.createElement("div");
      card.className = "payment-offer";
      card.innerHTML =
        '<div class="offer-headline"></div>' +
        '<div class="offer-incentive"></div>' +
        '<div class="offer-deposit">Deposit: <strong></strong></div>' +
        '<div class="offer-countdown"></div>' +
        '<div class="offer-actions">' +
        '  <button type="button" class="pay-now-btn">Pay Now</button>' +
        '  <button type="button" class="dismiss-btn">Maybe later</button>' +
        "</div>" +
        '<div class="payment-status-msg"></div>';

      card.querySelector(".offer-headline").textContent = config.offerHeadline;
      card.querySelector(".offer-incentive").textContent = config.incentive;
      card.querySelector(".offer-deposit strong").textContent = formatDollars(config.depositAmount);

      messagesEl.appendChild(card);
      messagesEl.scrollTop = messagesEl.scrollHeight;

      var payNowBtn = card.querySelector(".pay-now-btn");
      var dismissBtn = card.querySelector(".dismiss-btn");
      var countdownEl = card.querySelector(".offer-countdown");
      var statusEl = card.querySelector(".payment-status-msg");

      var secondsLeft = Math.round(config.countdownMinutes * 60);
      var countdownInterval = setInterval(function () {
        secondsLeft -= 1;
        if (secondsLeft <= 0) {
          clearInterval(countdownInterval);
          countdownEl.textContent = "This offer has expired";
          card.classList.add("expired");
          payNowBtn.disabled = true;
          return;
        }
        var mins = Math.floor(secondsLeft / 60);
        var secs = secondsLeft % 60;
        countdownEl.textContent =
          "Offer expires in " + mins + ":" + (secs < 10 ? "0" + secs : secs);
      }, 1000);
      countdownEl.textContent =
        "Offer expires in " + Math.floor(secondsLeft / 60) + ":" + (secondsLeft % 60 < 10 ? "0" : "") + (secondsLeft % 60);

      dismissBtn.addEventListener("click", function () {
        clearInterval(countdownInterval);
        card.remove();
        // The conversation has already ended and the lead is already captured —
        // dismissing the offer has no further effect.
      });

      payNowBtn.addEventListener("click", function () {
        payNowBtn.disabled = true;
        dismissBtn.disabled = true;
        statusEl.textContent = "";
        statusEl.style.color = "#616e7c";
        statusEl.textContent = "Setting up secure payment...";

        fetch(PAYMENT_INTENT_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lead_id: currentLeadId,
            amount: Math.round(config.depositAmount * 100),
          }),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (data) {
            if (!data.client_secret) {
              throw new Error("No client secret returned");
            }
            if (!config.stripePublishableKey) {
              throw new Error("Payments are not configured for this site (missing publishable key).");
            }

            clearInterval(countdownInterval);
            countdownEl.textContent = "";
            statusEl.textContent = "";

            openPaymentModal(
              data.client_secret,
              function onSuccess() {
                card.classList.add("success");
                card.innerHTML =
                  '<div class="offer-headline">Payment received!</div>' +
                  '<div class="offer-incentive">Your booking is confirmed. We will be in touch shortly to confirm the details.</div>';
              },
              function onCancel() {
                // Cancelling the modal returns the visitor to the payment offer card.
                payNowBtn.disabled = false;
                dismissBtn.disabled = false;
                statusEl.textContent = "";
              }
            );
          })
          .catch(function (err) {
            statusEl.style.color = "#b91c1c";
            statusEl.textContent = err.message || "Couldn't start the payment. Please try again.";
            payNowBtn.disabled = false;
            dismissBtn.disabled = false;
          });
      });
    }

    function sendToServer(message, displayUserMessage) {
      if (displayUserMessage) {
        appendMessage("user", message);
      }

      setInputEnabled(false);
      typingEl.classList.add("visible");

      fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          history: conversationHistory,
          business_name: config.businessName,
          services: config.services,
          location: config.location,
        }),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          typingEl.classList.remove("visible");

          conversationHistory.push({ role: "user", content: message });
          conversationHistory.push({ role: "assistant", content: data.message });

          appendMessage("assistant", data.message);

          if (data.lead_captured) {
            leadCaptured = true;
            currentLeadId = data.lead_id;
            appendSystemNote("This conversation has ended. Thanks for reaching out!");
            inputEl.placeholder = "Conversation complete";
            setInputEnabled(false);

            if (data.intent === "hot") {
              showPaymentOffer();
            }
          } else {
            setInputEnabled(true);
            inputEl.focus();
          }
        })
        .catch(function () {
          typingEl.classList.remove("visible");
          appendSystemNote("Something went wrong. Please try again.");
          setInputEnabled(true);
        });
    }

    function handleSend() {
      if (leadCaptured) return;
      var text = inputEl.value.trim();
      if (!text) return;
      inputEl.value = "";
      sendToServer(text, true);
    }

    sendBtn.addEventListener("click", handleSend);
    inputEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSend();
      }
    });

    function openPanel() {
      panel.classList.add("open");
      bubble.setAttribute("aria-expanded", "true");
      if (!panelOpened) {
        panelOpened = true;
        sendToServer("", false);
      }
      inputEl.focus();
    }

    function closePanel() {
      panel.classList.remove("open");
      bubble.setAttribute("aria-expanded", "false");
    }

    bubble.addEventListener("click", function () {
      if (panel.classList.contains("open")) {
        closePanel();
      } else {
        openPanel();
      }
    });

    closeBtn.addEventListener("click", closePanel);
  }

  if (document.body) {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
