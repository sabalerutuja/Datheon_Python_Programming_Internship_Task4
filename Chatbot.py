"""Rule-Based Interactive Terminal Assistant.

A customer-support chatbot that understands several kinds of questions using
keywords and regular expressions: business hours, contact info, greetings,
thanks, and product FAQs loaded from a JSON file.

Usage:
    python chatbot.py                 # loads faq.json if present, else built-in FAQs
    python chatbot.py my_faqs.json    # use a specific FAQ file

Type 'bye', 'exit' or 'quit' to leave.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

BOT_NAME = "Aria"
COMPANY = "ShopEasy"

BUSINESS_HOURS = {
    "weekdays": "9:00 AM - 6:00 PM (Monday to Friday)",
    "saturday": "10:00 AM - 4:00 PM",
    "sunday": "Closed",
}
CONTACT_INFO = "Email: support@shopeasy.example | Phone: +1-800-555-0199"

EXIT_WORDS = {"bye", "exit", "quit", "goodbye"}
CONFIRM_YES = {"yes", "y", "yeah", "yep", "sure", "ok", "okay"}
CONFIRM_NO = {"no", "n", "nope", "nah"}

STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "did", "i", "you", "your", "my", "me",
    "can", "how", "what", "when", "where", "to", "of", "for", "in", "on", "it", "and",
    "or", "we", "be", "have", "has", "with", "about", "please", "tell", "this", "that",
}

# Used when no FAQ JSON file is found, so the bot always works.
DEFAULT_FAQS = [
    {"question": "How long does shipping take?",
     "answer": "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days."},
    {"question": "What is your return policy?",
     "answer": "You can return any item within 30 days of delivery for a full refund, as long as it is unused."},
    {"question": "What payment methods do you accept?",
     "answer": "We accept credit and debit cards, PayPal, and UPI."},
    {"question": "How can I track my order?",
     "answer": "Use the tracking link in your confirmation email, or check 'My Orders' in your account."},
    {"question": "How do I reset my password?",
     "answer": "Click 'Forgot password' on the login page and follow the link we email you."},
    {"question": "Do your products come with a warranty?",
     "answer": "Yes, all products include a 1-year manufacturer warranty."},
]


# ---------- Text helpers ----------
def normalize(text):
    """Lowercase, strip whitespace, collapse repeated spaces."""
    return re.sub(r"\s+", " ", text.lower().strip())


def stem(word):
    """Very light stemming so 'returns'/'returning' match 'return'."""
    for suffix in ("ment", "ing", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    if len(word) > 3 and word[-1] == word[-2]:   # shipp -> ship
        word = word[:-1]
    return word


def keywords(text):
    words = re.findall(r"[a-z0-9']+", normalize(text))
    return {stem(w) for w in words if w not in STOPWORDS and len(w) > 1}


# ---------- FAQ loading ----------
def load_faqs(path):
    """Load FAQs from JSON. Accepts several common layouts; returns (faqs, source)."""
    q_keys = ("question", "q", "prompt", "title", "query")
    a_keys = ("answer", "a", "response", "reply", "text")
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return DEFAULT_FAQS, "built-in FAQs"
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Could not read {path} ({exc}). Using built-in FAQs.")
        return DEFAULT_FAQS, "built-in FAQs"

    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if lists:                              # {"faqs": [ ... ]}
            data = lists[0]
        else:                                  # {"question": "answer", ...}
            data = [{"question": k, "answer": v} for k, v in data.items() if isinstance(v, str)]

    faqs = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        low = {k.lower(): v for k, v in item.items()}
        q = next((low[k] for k in q_keys if k in low), None)
        a = next((low[k] for k in a_keys if k in low), None)
        if q and a:
            extra = low.get("keywords") or low.get("tags") or []
            if isinstance(extra, str):
                extra = [extra]
            faqs.append({"question": str(q), "answer": str(a), "extra": " ".join(map(str, extra))})

    if not faqs:
        print(f"No usable Q&A pairs found in {path}. Using built-in FAQs.")
        return DEFAULT_FAQS, "built-in FAQs"
    return faqs, f"{path} ({len(faqs)} FAQs)"


def faq_score(user_kw, faq):
    """How well the message covers the FAQ's keywords (0 to 1).

    Matching two keywords counts as a full match, so long questions are not
    penalized when the user asks in fewer words."""
    faq_kw = keywords(faq["question"] + " " + faq.get("extra", ""))
    if not faq_kw or not user_kw:
        return 0.0
    return len(faq_kw & user_kw) / min(len(faq_kw), 2)


# ---------- Intents (regex rules) ----------
def hours_reply(text):
    if re.search(r"\bsunday\b", text):
        return f"On Sundays we are: {BUSINESS_HOURS['sunday']}."
    if re.search(r"\bsaturday\b", text):
        return f"On Saturdays we are open {BUSINESS_HOURS['saturday']}."
    if re.search(r"\bweekends?\b", text):
        return (f"Weekend hours: Saturday {BUSINESS_HOURS['saturday']}; "
                f"Sunday {BUSINESS_HOURS['sunday'].lower()}.")
    now = datetime.now()
    open_now = now.weekday() < 5 and 9 <= now.hour < 18
    status = "We are open right now." if open_now else "We are currently closed."
    return (f"Our business hours are:\n"
            f"    Mon-Fri: {BUSINESS_HOURS['weekdays']}\n"
            f"    Saturday: {BUSINESS_HOURS['saturday']}\n"
            f"    Sunday: {BUSINESS_HOURS['sunday']}\n  {status}")


INTENTS = [
    ("hours", re.compile(r"\b(hours?|open(ing)?|clos(e|ed|ing)|timings?|schedule|working time)\b"), hours_reply),
    ("contact", re.compile(r"\b(contact|phone|call|email|e-mail|reach|support (team|agent)|human|agent)\b"),
     lambda t: f"You can reach us here -> {CONTACT_INFO}"),
    ("thanks", re.compile(r"\b(thanks|thank you|thx|cheers|appreciate)\b"),
     lambda t: "You're welcome! Anything else I can help with?"),
    ("help", re.compile(r"\b(help|options|what can you do|menu)\b"),
     lambda t: ("I can help with: business hours, contact details, shipping, returns, "
                "payments, order tracking, warranty and more. Just ask!")),
]
GREETING = re.compile(r"^(hi|hello|hey|hola|good (morning|afternoon|evening))\b")


# ---------- The bot ----------
class Chatbot:
    GREETING_STATE, ACTIVE, CONFIRMING = "greeting", "active", "confirming"

    def __init__(self, faqs, threshold=0.5, suggest_threshold=0.25):
        self.faqs = faqs
        self.threshold = threshold
        self.suggest_threshold = suggest_threshold
        self.state = self.GREETING_STATE
        self.pending = None       # FAQ we offered after a low-confidence match
        self.fallbacks = 0        # consecutive misunderstood messages
        self.last_topic = None    # remembered for short follow-ups

    def greet(self):
        self.state = self.ACTIVE
        return (f"Hi! I'm {BOT_NAME}, the {COMPANY} assistant. "
                "Ask me about hours, shipping, returns, payments and more. "
                "Type 'bye' to exit.")

    def respond(self, raw):
        text = normalize(raw)
        if not text:
            return "I didn't catch that. Could you type your question?"

        # Resolve a pending "Did you mean ...?" question first.
        if self.state == self.CONFIRMING:
            self.state = self.ACTIVE
            if text in CONFIRM_YES:
                faq, self.pending = self.pending, None
                self.fallbacks = 0
                return faq["answer"]
            self.pending = None
            if text in CONFIRM_NO:
                return "No problem. Could you rephrase your question?"

        replies = []

        # 1. Regex intents: every matching intent answers (multi-intent support).
        for name, pattern, handler in INTENTS:
            if pattern.search(text):
                replies.append(handler(text))
                self.last_topic = name

        # 2. Greeting (only if nothing else was asked).
        if GREETING.search(text) and not replies:
            self.fallbacks = 0
            return "Hello again! What can I help you with?"

        # 3. FAQ matching on the full message and on each clause of it.
        clauses = [c for c in re.split(r"\band\b|\balso\b|\bplus\b|[?;,.]", text) if c.strip()]
        scored = {}
        for chunk in [text] + clauses:
            user_kw = keywords(chunk)
            for i, faq in enumerate(self.faqs):
                scored[i] = max(scored.get(i, 0.0), faq_score(user_kw, faq))
        ranked = sorted(scored.items(), key=lambda kv: kv[1], reverse=True)
        strong = [i for i, s in ranked if s >= self.threshold][:2]
        for i in strong:
            replies.append(self.faqs[i]["answer"])
            self.last_topic = self.faqs[i]["question"]

        if replies:
            self.fallbacks = 0
            return "\n  ".join(replies)

        # 4. Low-confidence match: offer the closest FAQ and ask to confirm.
        if ranked and ranked[0][1] >= self.suggest_threshold:
            self.pending = self.faqs[ranked[0][0]]
            self.state = self.CONFIRMING
            return f"I'm not sure I understood. Did you mean: \"{self.pending['question']}\" (yes/no)?"

        # 5. Graceful fallback, escalating after repeated misses.
        self.fallbacks += 1
        if self.fallbacks >= 2:
            return ("Sorry, I'm still having trouble. Type 'help' to see what I can do, "
                    f"or contact a human -> {CONTACT_INFO}")
        return ("Sorry, I didn't understand that. You can ask about business hours, "
                "shipping, returns, payments or order tracking.")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "faq.json"
    faqs, source = load_faqs(path)
    bot = Chatbot(faqs)
    print(f"[Loaded {source}]\n")
    print(f"{BOT_NAME}: {bot.greet()}\n")

    while True:
        try:
            user = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{BOT_NAME}: Goodbye!")
            break
        if normalize(user) in EXIT_WORDS:
            print(f"{BOT_NAME}: Thanks for chatting with {COMPANY}. Goodbye!")
            break
        print(f"{BOT_NAME}: {bot.respond(user)}\n")


if __name__ == "__main__":
    main()