# Phrases that clearly try to read or override the system rules
DIRECT_PHRASES = [
    "system prompt",
    "پرامپت سیستم",
    "قوانین سیستمی",
    "دستورات سیستمی",
    "دستورالعمل سیستمی",
    "developer mode",
    "jailbreak",
]

# A "forget/ignore" word together with a "rules/instructions" word is suspicious
OVERRIDE_WORDS = ["فراموش کن", "نادیده بگیر", "ignore", "forget", "disregard"]
TARGET_WORDS = ["دستور", "قوانین", "قوانینت", "دستورالعمل", "instruction", "rules", "prompt", "پرامپت"]

REFUSAL_MESSAGE = "متأسفم، نمی‌توانم این درخواست را انجام دهم. چطور می‌توانم در مورد فروشگاه کمکتان کنم؟"


def normalize(text: str) -> str:
    """Make text easier to compare: lowercase, one kind of Persian letters."""
    text = text.lower()
    text = text.replace("\u200c", " ")  # half-space (ZWNJ) becomes a normal space
    text = text.replace("ي", "ی").replace("ك", "ک")  # Arabic letters become Persian
    return text


def is_suspicious(text: str) -> bool:
    """Return True if the text looks like a prompt injection attempt."""
    text = normalize(text)

    if any(phrase in text for phrase in DIRECT_PHRASES):
        return True

    has_override = any(word in text for word in OVERRIDE_WORDS)
    has_target = any(word in text for word in TARGET_WORDS)
    return has_override and has_target