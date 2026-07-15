"""Item-code generation helpers."""


def generate_next_item_barcode(db, prefix):
    number = db.execute("SELECT nextval('item_barcode_number_seq') AS number").fetchone()["number"]
    return f"{prefix}-{number:06d}"
