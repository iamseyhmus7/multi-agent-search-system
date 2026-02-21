import re
from datetime import datetime


def parse_iso_duration(duration_str: str) -> int:
    """
    PT4H35M → toplam dakika
    """
    hours = 0
    minutes = 0

    h_match = re.search(r"(\d+)H", duration_str)
    m_match = re.search(r"(\d+)M", duration_str)

    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))

    return hours * 60 + minutes


def calculate_duration_minutes(offer):
    return parse_iso_duration(offer["raw_duration"])


def count_stops(offer):
    return offer["segments_count"] - 1