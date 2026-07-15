"""Item form parsing helpers."""

from datetime import datetime


def parse_expiration_date(value):
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def get_item_form_data(form, require_barcode=True):
    expiration_date = parse_expiration_date(form.get("expiration_date", ""))

    data = {
        "barcode": form.get("barcode", "").strip(),
        "name": form.get("name", "").strip(),
        "bin_location": form.get("bin_location", "").strip(),
        "room": form.get("room", "").strip(),
        "company": form.get("company", "").strip(),
        "location": form.get("location", "").strip(),
        "expiration_date": expiration_date,
        "notes": form.get("notes", "").strip(),
    }

    try:
        data["quantity"] = int(form.get("quantity", "0"))
        data["minimum_quantity"] = int(form.get("minimum_quantity", "0"))
    except ValueError:
        data["quantity"] = 0
        data["minimum_quantity"] = 0
        return data, "Quantity values must be numbers."

    if require_barcode and not data["barcode"]:
        return data, "Code, name, bin location, and room are required."

    if not data["name"] or not data["bin_location"] or not data["room"]:
        if require_barcode:
            return data, "Code, name, bin location, and room are required."
        return data, "Name, bin location, and room are required."

    if data["quantity"] < 0 or data["minimum_quantity"] < 0:
        return data, "Quantity values cannot be negative."

    return data, None
