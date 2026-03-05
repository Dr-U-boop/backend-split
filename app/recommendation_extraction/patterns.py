from __future__ import annotations

import re
from typing import Iterable


FLOAT_RE = r"[-+]?\d+(?:\.\d+)?"
TIME_TOKEN_RE = r"(?:[01]?\d|2[0-3])(?::[0-5]?\d)?"

RE_NUMBER = re.compile(FLOAT_RE)
RE_RANGE = re.compile(rf"(?P<min>{FLOAT_RE})\s*[-]\s*(?P<max>{FLOAT_RE})")
RE_PERCENT = re.compile(rf"(?P<value>{FLOAT_RE})\s*%")
RE_TEMP_BASAL = re.compile(
    rf"(?:врем\w*\s+баз\w*|temp\s+basal).{{0,20}}?(?P<value>[-+]?{FLOAT_RE})\s*%",
)
RE_BASAL_PERCENT = re.compile(
    rf"(?:базал\w*|баз\w*).{{0,20}}?(?P<value>[-+]?{FLOAT_RE})\s*%"
)
RE_TIME_INTERVAL = re.compile(
    rf"(?:с|от)\s*(?P<start>{TIME_TOKEN_RE})\s*(?:до|по|-)\s*(?P<end>{TIME_TOKEN_RE})"
)
RE_ANY_TIME_DASH = re.compile(
    r"\b(?P<start>(?:[01]?\d|2[0-3]):[0-5]\d)\s*-\s*(?P<end>(?:[01]?\d|2[0-3]):[0-5]\d)\b"
)
RE_BASAL_RATE = re.compile(rf"(?P<value>{FLOAT_RE})\s*ед/ч\b")
RE_BASAL_RATE_SOFT = re.compile(
    rf"(?:баз\w*\s+(?:скор\w*)?|базал\w*).{{0,20}}?(?P<value>{FLOAT_RE})(?:\s*ед/ч)?"
)
RE_CARB_RATIO = re.compile(rf"1\s*ед\s*/\s*(?P<grams>{FLOAT_RE})\s*г\b")
RE_CARB_RATIO_COLON = re.compile(
    rf"(?:угл\w*|коэф\w*|коэфф\w*|ук|завтрак|обед|ужин).{{0,20}}?1\s*:\s*(?P<grams>{FLOAT_RE})"
)
RE_CORRECTION_FACTOR = re.compile(
    rf"1\s*ед\s*/\s*(?P<mmol>{FLOAT_RE})\s*ммоль/л\b"
)
RE_CORRECTION_FACTOR_EQ = re.compile(
    rf"1\s*ед\s*(?:=|/)\s*(?P<mmol>{FLOAT_RE})\s*ммоль(?:/л)?\b"
)
RE_CORRECTION_FACTOR_COLON = re.compile(
    rf"(?:чувств\w*|фактор\w*).{{0,20}}?1\s*:\s*(?P<mmol>{FLOAT_RE})"
)
RE_TARGET_RANGE = re.compile(
    rf"(?P<min>{FLOAT_RE})\s*-\s*(?P<max>{FLOAT_RE})(?:\s*ммоль/л\b)?"
)
RE_TARGET_SINGLE = re.compile(rf"(?P<value>{FLOAT_RE})(?:\s*ммоль/л\b)?")
RE_PREBOLUS = re.compile(
    rf"(?:предболюс|prebolus|предболус|пред-болюс).{{0,12}}?(?P<value>{FLOAT_RE})\s*(?P<unit>мин|ч)\b"
)
RE_ACTIVE_INSULIN = re.compile(
    rf"(?:активн\w*\s+инсул\w*|длительн\w*\s+инсулина|dia|актив\w*\s+инс\w*).{{0,12}}?(?P<value>{FLOAT_RE})\s*(?P<unit>ч|мин)\b"
)
RE_CORRECTION_INTERVAL = re.compile(
    rf"(?:не\s+корректир\w*\s+раньше|не\s+корриг\w*\s+раньше|коррекц\w*\s+не\s+раньше(?:\s+чем\s+через)?|интервал\s+коррекц\w*|коррекц\w*\s+интервал\w*|коррект\w*\s+интервал\w*|не\s+делать\s+повтор\s+коррекц\w*|интрвал\w*\s+не\s+ранее).{{0,30}}?(?P<value>{FLOAT_RE})\s*(?P<unit>ч|мин)\b"
)
RE_LOW_ALERT = re.compile(
    rf"(?:порог\s+низк\w*\s+глюк\w*|низк\w*\s+порог|гипо\s+порог|порог\s+низкой).{{0,20}}?(?P<value>{FLOAT_RE})(?:\s*ммоль/л)?"
)
RE_HIGH_ALERT = re.compile(
    rf"(?:порог\s+высок\w*\s+глюк\w*|высок\w*\s+порог|гипер\s+порог|порог\s+высокой).{{0,20}}?(?P<value>{FLOAT_RE})(?:\s*ммоль/л)?"
)
RE_DUAL_BOLUS = re.compile(
    rf"(?P<first>{FLOAT_RE})\s*%\s*(?:сразу|немедленно)?\s*(?:и|/)\s*(?P<second>{FLOAT_RE})\s*%\s*(?:за|на)\s*(?P<duration>{FLOAT_RE})\s*(?P<unit>ч|мин)"
)


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_time_token(token: str | None) -> str | None:
    if not token:
        return None
    token = token.strip()
    if ":" in token:
        h, m = token.split(":", maxsplit=1)
        hh = int(h)
        mm = int(m)
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"
        return None
    hour = int(token)
    if 0 <= hour <= 23:
        return f"{hour:02d}:00"
    return None


def first_match(patterns: Iterable[re.Pattern[str]], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match
    return None
