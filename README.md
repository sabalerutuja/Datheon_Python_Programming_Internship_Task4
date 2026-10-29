# Rule-Based Interactive Terminal Assistant

A customer-support chatbot for the terminal, built with Python. It understands questions using keywords and regular expressions, answers questions about business hours and product FAQs, and handles unrecognized questions gracefully. No machine learning or external libraries are needed.

## Features

- Parses user input with `re` (lowercasing, whitespace cleanup, regex keyword extraction)
- Answers several questions in a single message (for example: "what are your hours and how do I track my order?")
- Business hours intent, including specific questions such as "are you open on Sunday?"
- Contact, help and thanks intents
- Product FAQs loaded from a JSON file, with a built-in set used if no file is found
- Conversational state management: greeting, answering, confirming, exit
- "Did you mean ...?" confirmation when a match is uncertain
- Fallback replies for unrecognized queries, which point to contact details after repeated misses
- Clean exit commands: `bye`, `exit`, `quit`

## Requirements

- Python 3 (standard library only: `re`, `json`, `pathlib`, `datetime`)

## Usage

Run with the default FAQ file (`faq.json` in the same folder):

```
python chatbot.py
```

Run with a specific FAQ file:

```
python chatbot.py my_faqs.json
```

If no FAQ file is found, the bot uses its built-in FAQs.

## FAQ file format

A JSON list of question and answer pairs. These layouts are accepted:

```json
[
  {"question": "How long does shipping take?", "answer": "3-5 business days."}
]
```

```json
{"faqs": [{"q": "Do you ship internationally?", "a": "Yes, to 40 countries."}]}
```

```json
{"What is your return policy?": "Returns are accepted within 30 days."}
```

An optional `keywords` field on each entry adds extra words the bot can match on.

## Example conversation

```
Aria: Hi! I'm Aria, the ShopEasy assistant. Ask me about hours, shipping, returns, payments and more. Type 'bye' to exit.

You: what are your hours and how do I track my order?
Aria: Our business hours are:
    Mon-Fri: 9:00 AM - 6:00 PM (Monday to Friday)
    Saturday: 10:00 AM - 4:00 PM
    Sunday: Closed
  We are open right now.
  Use the tracking link in your confirmation email, or check 'My Orders' in your account.

You: are you open on sunday
Aria: On Sundays we are: Closed.

You: asdf
Aria: Sorry, I didn't understand that. You can ask about business hours, shipping, returns, payments or order tracking.

You: bye
Aria: Thanks for chatting with ShopEasy. Goodbye!
```

## How it works

1. **Normalize:** the message is lowercased and cleaned up.
2. **Intent rules:** regular expressions check for hours, contact, thanks and help. Every rule that matches adds to the reply, which is how multiple questions are answered at once.
3. **FAQ matching:** keywords from the message are compared with each FAQ question, on the whole message and on each clause of it.
4. **Confirmation:** a weak match triggers a "Did you mean ...?" question.
5. **Fallback:** if nothing matches, the bot asks the user to rephrase, and after two misses it suggests contacting support.

## Customizing

Change the company name, business hours and contact details in the constants at the top of `chatbot.py`.

## Files

| File | Description |
|------|-------------|
| `chatbot.py` | Main script |
| `faq.json` | FAQ dataset (optional) |
