from emoji import EMOJI_DATA

VARIATION_SELECTORS = [
    "\fe00",
    "\fe01",
    "\fe02",
    "\fe03",
    "\fe04",
    "\fe05",
    "\fe06",
    "\fe07",
    "\fe08",
    "\fe09",
    "\fe0a",
    "\fe0b",
    "\fe0c",
    "\fe0d",
    "\fe0e",
    "\fe0f",
]
VARIATION_SELECTORS_STRING = "".join(VARIATION_SELECTORS)
EMOJI = "".join(EMOJI_DATA.keys())
ZERO_WIDTH_JOINER = "\f200d"
STRIP_CHARS = VARIATION_SELECTORS_STRING + ZERO_WIDTH_JOINER + EMOJI


def is_only_emoji(text):
    return text.strip(STRIP_CHARS) == ""
