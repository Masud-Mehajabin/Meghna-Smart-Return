from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re


def normalize_scientific_notation(value: str, is_identifier: bool = True):
    """
    Convert scientific notation (e.g. '4.46836E+11', '2.10111E+14', '3.251E+13', '3.25226E+11')
    or float strings (e.g. '325226150158.0') to exact integer string representations.
    """
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ("none", "null", "nan"):
        return None

    # Clean float-style integer suffixes like "325226150158.0" or "325226150158.00" for identifiers
    if is_identifier and re.match(r"^\d+\.0+$", val_str):
        return val_str.split(".")[0]

    # Check for scientific notation (E or e)
    if not re.search(r"[eE]", val_str):
        return val_str

    try:
        dec = Decimal(val_str)
        formatted = format(dec, "f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted
    except InvalidOperation:
        return val_str


def strip_leading_zeros(value: str):
    """
    Strip leading zeros from identifier strings like EXP No or comma-separated lists like PURPOSE_CODE_SBB
    e.g. "000032520020432026" -> "32520020432026"
    e.g. "0040,0130" -> "40,130"
    """
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str:
        return None

    if "," in val_str:
        parts = [p.strip().lstrip("0") for p in val_str.split(",")]
        cleaned_parts = [p if p != "" else "0" for p in parts]
        return ",".join(cleaned_parts)

    stripped = val_str.lstrip("0")
    return stripped if stripped != "" else "0"


DATE_FORMATS = [
    "%d-%b-%Y",   # 15-JUN-2026 / 15-Jun-2026
    "%d-%b-%y",   # 05-JUL-26 / 05-Jul-26
    "%d-%B-%Y",   # 15-JUNE-2026
    "%d-%B-%y",   # 15-JUNE-26
    "%d/%m/%Y",   # 15/06/2026
    "%d/%m/%y",   # 15/06/26
    "%Y-%m-%d",   # 2026-06-15
    "%y-%m-%d",   # 26-06-15
    "%d-%m-%Y",   # 15-06-2026
    "%d-%m-%y",   # 15-06-26
    "%d.%m.%Y",   # 15.06.2026
    "%d.%m.%y",   # 15.06.26
]


def parse_oracle_date(value: str):
    """
    Parse a date string from CSV and return a Python date object.
    oracledb will bind Python date → Oracle DATE correctly.
    Returns None if unparseable.
    """
    if not value or str(value).strip() in ("", "None"):
        return None
    v = str(value).strip()
    # Title-case so 'JUN' → 'Jun' for %b matching
    v_titled = v.title()
    for fmt in DATE_FORMATS:
        for candidate in (v, v_titled):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    return None    # unparseable – will go to failed log


def clean_numeric(value: str, *args, **kwargs):
    """
    Strip thousands commas and format numeric/amount/decimal values to string with exactly 2 decimal places:
    - 4208.0000  -> "4208.00"
    - 23191.2900 -> "23191.29"
    - 0.0000     -> "0.00"
    - 24001.3200 -> "24001.32"
    - 158.1800   -> "158.18"
    """
    if value is None or str(value).strip() in ("", "None", "null", "NULL", "nan", "NaN"):
        return None
    return format_2_decimal_string(value, default=str(value).strip())


def format_2_decimal_string(value: str, default: str = "") -> str:
    """
    Takes any input value (Decimal, float, int, str) and returns a clean string with exactly 2 decimal places.
    - 2000.923   -> "2000.92"
    - 2000.1     -> "2000.10"
    - 13194.1100 -> "13194.11"
    - 0.0000     -> "0.00"
    - 11700.0000 -> "11700.00"
    - 0          -> "0.00"
    """
    if value is None or str(value).strip() in ("", "None", "null", "NULL", "nan", "NaN"):
        return default
    cleaned = re.sub(r",", "", str(value).strip())
    try:
        d = Decimal(cleaned)
        q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{q:.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return str(value).strip()


def is_numeric_decimal_string(value: str) -> bool:
    """Check if string is a numeric decimal value (e.g. '11600.0000', '0.0000', '50.00')."""
    if value is None or str(value).strip() in ("", "None", "null", "NULL", "nan", "NaN"):
        return False
    cleaned = re.sub(r",", "", str(value).strip())
    try:
        Decimal(cleaned)
        return True
    except InvalidOperation:
        return False


def clean_integer(value: str, *args, **kwargs):
    """
    Format numeric value to clean integer string without decimal zeroes:
    - "3.00" -> "3"
    - "3.0"  -> "3"
    - "3"    -> "3"
    - 0      -> "0"
    """
    if value is None or str(value).strip() in ("", "None", "null", "NULL", "nan", "NaN"):
        return None
    cleaned = re.sub(r",", "", str(value).strip())
    try:
        d = Decimal(cleaned)
        return str(int(d))
    except (InvalidOperation, TypeError, ValueError):
        return str(value).strip()


def clean_currency_code(value: str, *args, **kwargs):
    """
    Format currency code into exact 2-digit string format:
    - "001" -> "01"
    - "01"  -> "01"
    - "1"   -> "01"
    - "098" -> "98"
    - "98"  -> "98"
    """
    if value is None or str(value).strip() in ("", "None", "null", "NULL", "nan", "NaN"):
        return None
    val_str = str(value).strip().lstrip("0")
    if not val_str:
        return "00"
    return val_str.zfill(2)






