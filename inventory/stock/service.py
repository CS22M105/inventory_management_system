"""Stock transaction service helpers."""


def process_stock_transaction(db, user_id, barcode, form, audit_callback=None):
    transaction_type = form.get("transaction_type", "").strip()
    lab_instructor = form.get("lab_instructor", "").strip()
    topic_of_day = form.get("topic_of_day", "").strip()
    notes = form.get("notes", "").strip()

    try:
        quantity = int(form.get("quantity", "1"))
    except ValueError:
        return None, "Quantity must be a number.", 400

    if not barcode:
        return None, "Barcode is required.", 400
    if transaction_type not in {"add", "remove"}:
        return None, "Choose Add Stock or Remove Stock.", 400
    if quantity <= 0:
        return None, "Quantity must be greater than zero.", 400
    if not lab_instructor:
        return None, "Lab Instructor is required.", 400
    if not topic_of_day:
        return None, "Topic of the Day is required.", 400
    if not notes:
        return None, "Notes are required.", 400

    item = db.execute(
        "SELECT id, name, quantity FROM items WHERE barcode = %s",
        (barcode,),
    ).fetchone()
    if item is None:
        return None, "No item was found for that barcode.", 404
    if transaction_type == "remove" and quantity > item["quantity"]:
        return None, f"Cannot remove {quantity}. Only {item['quantity']} available.", 400

    new_quantity = item["quantity"] + quantity if transaction_type == "add" else item["quantity"] - quantity
    db.execute("UPDATE items SET quantity = %s WHERE id = %s", (new_quantity, item["id"]))
    db.execute(
        """
        INSERT INTO transactions (
            user_id, item_id, transaction_type, quantity,
            lab_instructor, topic_of_day, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, item["id"], transaction_type, quantity, lab_instructor, topic_of_day, notes),
    )
    if audit_callback is not None:
        audit_callback(db, item, transaction_type, quantity, new_quantity)
    db.commit()
    return f"{item['name']} updated successfully. New quantity: {new_quantity}.", None, 200


def get_stock_item(db, barcode):
    return db.execute(
        """
        SELECT id, barcode, name, room, bin_location, quantity
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()
