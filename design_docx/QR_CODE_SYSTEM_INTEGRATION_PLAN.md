# QR Code System Integration Plan

Date: June 30, 2026

Project: Katz Nursing School Inventory Management System

## Purpose

This document explains how to merge a self-generated QR code system into the current Flask inventory application without breaking the working local system.

The goal is:

```text
Faculty/Admin adds a new item
System automatically assigns an internal item code
System generates a QR code label for that item
User prints and pastes the label on the item/bin
Later, user scans the QR code with a camera
The stock action page opens already linked to that item
User adds/removes stock
System updates inventory and records a transaction
```

This plan is written for the current project structure:

```text
app.py
schema.sql
requirements.txt
templates/
static/
```

It does not require splitting `app.py` yet. The QR feature can be added safely first, then the app can be refactored later when features are stable.

---

## Current System Behavior

The current system already has the foundation needed for QR integration.

Current database table:

```sql
items (
    id SERIAL PRIMARY KEY,
    barcode TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    bin_location TEXT NOT NULL,
    room TEXT NOT NULL,
    company TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    expiration_date TEXT DEFAULT '00/00/0000',
    notes TEXT
)
```

Current item creation:

```text
Route: /items/new
Template: templates/item_new.html
Current behavior: user manually enters barcode
```

Current stock workflow:

```text
Route: /scan
Template: templates/scan.html
Current behavior: user scans/types barcode, chooses add/remove stock, enters transaction details
```

Current transaction table already records:

```text
date
time
action type
quantity
lab instructor
topic of day
notes
user
item
```

This means the QR system should not replace the existing scan workflow. It should extend it.

---

## Important Concept

A QR code is not the inventory item.

A QR code is only a machine-readable version of text.

For this system, the QR code should store a URL like:

```text
https://inventory.katz.yu.edu/items/KATZ-NURS-000014/stock
```

When the camera scans the QR code:

```text
Browser opens the URL
Flask reads KATZ-NURS-000014 from the URL
Flask finds the item in PostgreSQL
Flask shows the stock action page for that item
```

The item details stay in the database. The QR code only points to the item.

This is important because item details can change:

```text
quantity changes
room changes
bin changes
vendor changes
minimum quantity changes
notes change
```

The QR label does not need to be reprinted every time those details change.

---

## Recommended Internal Code Format

Because this is a personalized university system, do not use retail UPC codes.

Use internal university codes.

Recommended format:

```text
KATZ-NURS-000001
KATZ-NURS-000002
KATZ-NURS-000003
```

Why this format:

- Clear ownership: Katz Nursing
- Easy to read by humans
- Easy to print
- Easy to search
- URL-safe because it uses letters, numbers, and hyphens
- Does not conflict with manufacturer barcodes
- Works for items that do not have existing barcodes

The existing `items.barcode` column can continue to store this value. We do not need to rename the column immediately.

Recommended meaning:

```text
barcode column = internal item code
QR code image = generated from a URL that contains the internal item code
```

---

## Do We Store QR Images In The Database?

Recommended answer: no.

Store this:

```text
KATZ-NURS-000014
```

Generate this when needed:

```text
QR image for /items/KATZ-NURS-000014/stock
```

Why not store QR images:

- Avoids large database rows
- Avoids storing generated files
- QR can always be regenerated
- Cleaner backups
- Easier cloud deployment
- URL may change when moving from local to cloud

The system should generate the QR image dynamically on the label page.

---

## Required Python Package

Add this dependency:

```text
qrcode[pil]
```

In `requirements.txt`:

```text
qrcode[pil]>=7.4,<8.0
```

This library uses Pillow to create PNG images.

It can generate QR images inside Flask.

No paid plugin is required.
No external QR website is required.
No separate QR software is required.

---

## Environment Configuration

The QR code needs to know the public base URL of the app.

Local development:

```text
http://127.0.0.1:5001
```

Cloud production:

```text
https://inventory.katz.yu.edu
```

Recommended new environment variable:

```text
APP_BASE_URL=http://127.0.0.1:5001
```

Add to `.env.example`:

```text
APP_BASE_URL=http://127.0.0.1:5001
```

In production:

```text
APP_BASE_URL=https://inventory.katz.yu.edu
```

Why this matters:

- If the QR code contains `127.0.0.1`, it only works on the same computer.
- A phone camera cannot use the computer's `127.0.0.1`.
- For phones/tablets, the QR URL must point to a real cloud URL or a local network URL.

Temporary local network example:

```text
http://192.168.1.25:5001/items/KATZ-NURS-000014/stock
```

Production example:

```text
https://inventory.katz.yu.edu/items/KATZ-NURS-000014/stock
```

---

## Database Design

### Keep Existing Column

Do not remove the current `barcode` column.

Current:

```sql
barcode TEXT NOT NULL UNIQUE
```

Keep it.

This avoids breaking:

- existing items
- existing scan workflow
- transaction history joins
- CSV exports
- item edit page
- low stock page

### Add A PostgreSQL Sequence

To generate internal item codes safely, use a PostgreSQL sequence.

Recommended sequence:

```sql
CREATE SEQUENCE IF NOT EXISTS item_barcode_number_seq START WITH 1;
```

Why sequence is better than `COUNT(*) + 1`:

- Safe when two users add items at the same time
- Avoids duplicate numbers
- Database handles the increment
- Works well in production

### Generated Code Logic

Pseudo-code:

```python
number = nextval('item_barcode_number_seq')
barcode = f"KATZ-NURS-{number:06d}"
```

Example:

```text
number = 14
barcode = KATZ-NURS-000014
```

### Existing Items Migration

If existing items already have manually entered barcodes, do not overwrite them automatically.

Safer approach:

1. Keep existing barcodes.
2. Generate automatic codes only for new items.
3. Optional later: add a one-time admin tool to convert old barcodes to `KATZ-NURS-000001` format.

If some existing items already use the `KATZ-NURS-000014` format, set the sequence to start after the highest existing number.

Example SQL idea:

```sql
SELECT MAX(CAST(SUBSTRING(barcode FROM 'KATZ-NURS-([0-9]+)') AS INTEGER))
FROM items
WHERE barcode ~ '^KATZ-NURS-[0-9]+$';
```

Then:

```sql
SELECT setval('item_barcode_number_seq', highest_number);
```

This prevents the app from generating a code that already exists.

### Should We Add More Columns?

Minimum change:

```text
No new columns required
```

Optional future columns:

```sql
barcode_generated BOOLEAN NOT NULL DEFAULT TRUE
qr_label_printed_at TIMESTAMP
qr_label_printed_by INTEGER REFERENCES users(id)
```

Recommendation:

Do not add optional tracking columns in the first QR implementation. Keep the first version small and safe.

---

## Main Feature Pieces

The QR system should be added in phases.

### Phase 1: Automatic Internal Barcode Generation

Goal:

```text
New items receive KATZ-NURS-000001 style codes automatically.
```

Current behavior:

```text
Add New Item requires manual barcode entry.
```

New behavior:

```text
Barcode field can be optional or hidden.
System generates barcode during item creation.
```

Recommended UI:

On `templates/item_new.html`:

- Remove `required` from barcode field, or hide it.
- Show helper text:

```text
Leave blank to auto-generate a Katz Nursing inventory code.
```

Backend logic:

```text
If barcode is blank:
    generate KATZ-NURS-000001 style code
If barcode is entered:
    use entered barcode after duplicate check
```

Why keep manual option:

- Some items may already have manufacturer barcodes.
- Existing workflow remains possible.
- Safer transition.

Recommended first implementation:

```text
Make barcode optional on Add New Item only.
Keep barcode editable on Edit Item for faculty/admin.
```

Later, if the university wants strict internal codes:

```text
Hide manual barcode entry completely.
```

---

### Phase 2: Item Detail Page

Add a page that displays all item information.

Recommended route:

```text
/items/<barcode>
```

Example:

```text
/items/KATZ-NURS-000014
```

Purpose:

- Shows item details
- Gives user a clear page connected to the QR label
- Provides buttons for:
  - Stock Action
  - Print Label
  - Edit Item, if faculty/admin

Page should show:

```text
Item Name
Internal Code
Vendor
Room
Bin
Current Quantity
Minimum Quantity
Expiration Date
Notes
Low-stock status
```

Recommended template:

```text
templates/item_detail.html
```

Access:

```text
Any logged-in user can view item detail.
Faculty/admin can edit item.
```

Why this should come before label printing:

- QR codes need a useful destination page.
- The detail page confirms the item code works.

---

### Phase 3: Printable QR Label Page

Add a page dedicated to printing the item label.

Recommended route:

```text
/items/<barcode>/label
```

Example:

```text
/items/KATZ-NURS-000014/label
```

Recommended template:

```text
templates/item_label.html
```

The label should include:

```text
Katz Nursing Inventory
Item Name
KATZ-NURS-000014
QR Code
Room
Bin
Optional: Vendor
Optional: Expiration Date
```

Example label content:

```text
Katz Nursing Inventory
Medium Nitrile Gloves
KATZ-NURS-000014
[QR CODE]
Room: Medication Room
Bin: Shelf A, Bin 3
```

Recommended buttons:

```text
Print Label
Back to Item
Back to All Items
```

Print behavior:

```javascript
window.print()
```

Recommended CSS:

```css
@media print {
    header,
    nav,
    footer,
    .no-print {
        display: none;
    }

    .qr-label {
        width: 2.4in;
        min-height: 1.2in;
    }
}
```

Label size depends on printer:

```text
Brother QL labels: often 2.4 inch width
Zebra labels: configurable
Avery sheets: depends on sheet layout
```

Start with browser print. Do printer-specific optimization later.

---

### Phase 4: QR Image Generation Route

Recommended route:

```text
/items/<barcode>/qr.png
```

Example:

```text
/items/KATZ-NURS-000014/qr.png
```

Purpose:

Returns a PNG image of the QR code.

The QR code should encode:

```text
{APP_BASE_URL}/items/{barcode}/stock
```

Example:

```text
https://inventory.katz.yu.edu/items/KATZ-NURS-000014/stock
```

The label template can display:

```html
<img src="{{ url_for('item_qr_png', barcode=item['barcode']) }}" alt="QR code">
```

Benefits:

- Browser can load QR image normally
- No need to save image files
- QR regenerates whenever page loads
- Easy to test

Pseudo-code:

```python
@app.route("/items/<barcode>/qr.png")
def item_qr_png(barcode):
    require_login()
    item = get item by barcode
    if not found:
        abort(404)

    stock_url = f"{APP_BASE_URL}{url_for('item_stock', barcode=barcode)}"
    image = qrcode.make(stock_url)
    return Response(image_bytes, mimetype="image/png")
```

Important:

Use `url_for(..., _external=False)` with `APP_BASE_URL`, or use `url_for(..., _external=True)` if the deployed host is configured correctly.

Recommended for consistency:

```python
base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
stock_url = f"{base_url}{url_for('item_stock', barcode=barcode)}"
```

---

### Phase 5: Stock Action Page Opened From QR

Recommended route:

```text
/items/<barcode>/stock
```

Example:

```text
/items/KATZ-NURS-000014/stock
```

Recommended template:

```text
templates/item_stock.html
```

Purpose:

This page replaces manual barcode entry for QR use.

Instead of asking for barcode, it already knows the item.

Page should show:

```text
Item Name
Internal Code
Current Quantity
Room
Bin
```

Then show the transaction form:

```text
Action: Add Stock / Remove Stock
Quantity
Lab Instructor
Topic of the Day
Notes
Submit Inventory Action
```

Hidden field:

```html
<input type="hidden" name="barcode" value="{{ item['barcode'] }}">
```

Or better:

Do not post barcode from the browser. Use the barcode from the URL.

Recommended POST route:

```text
POST /items/<barcode>/stock
```

Why use URL barcode instead of hidden field:

- Less chance of tampering
- The route already identifies the item
- Cleaner logic

Behavior:

```text
GET /items/KATZ-NURS-000014/stock
    show pre-filled stock page

POST /items/KATZ-NURS-000014/stock
    validate action, quantity, instructor, topic, notes
    find item by barcode
    update quantity
    insert transaction
    show success message
```

Reuse current `/scan` transaction logic.

Do not duplicate all logic long term.

Recommended helper:

```python
def process_stock_transaction(barcode, form_data):
    validate form
    find item
    check remove quantity
    update items.quantity
    insert transaction
    commit
    return success/error
```

Then both routes can use it:

```text
/scan
/items/<barcode>/stock
```

This prevents bugs where scan page and QR stock page behave differently.

---

## How The Complete Workflow Works

### New Item Workflow

1. Faculty/admin opens:

```text
Items -> Add New Item
```

2. Faculty/admin enters:

```text
Item Name
Vendor
Room
Bin
Quantity
Minimum Quantity
Expiration Date
Notes
```

3. Barcode field is left blank.

4. Flask generates:

```text
KATZ-NURS-000014
```

5. Flask saves item:

```sql
INSERT INTO items (barcode, name, room, bin_location, ...)
```

6. Flask redirects to:

```text
/items/KATZ-NURS-000014/label
```

7. User prints the label.

8. User pastes label on item/bin.

### Daily Stock Workflow With QR

1. User scans QR code with phone/tablet/camera.

2. QR opens:

```text
/items/KATZ-NURS-000014/stock
```

3. If user is not logged in:

```text
Redirect to login
```

4. After login:

Best later improvement:

```text
Return user to the scanned QR URL
```

Initial implementation can simply show login and user can rescan.

5. Stock page displays:

```text
Medium Nitrile Gloves
Current Quantity: 20
Room: Medication Room
Bin: Shelf A, Bin 3
```

6. User selects:

```text
Add Stock
or
Remove Stock
```

7. User enters:

```text
Quantity
Lab Instructor
Topic
Notes
```

8. System updates item quantity.

9. System records transaction.

10. System shows success message.

---

## How To Fit This Into Current Files

### `requirements.txt`

Add:

```text
qrcode[pil]>=7.4,<8.0
```

Then run:

```bash
pip install -r requirements.txt
```

### `.env.example`

Add:

```text
APP_BASE_URL=http://127.0.0.1:5001
BARCODE_PREFIX=KATZ-NURS
```

`BARCODE_PREFIX` is optional but useful.

If the university later wants a different prefix:

```text
BARCODE_PREFIX=YU-KATZ-NURS
```

### `schema.sql`

Add sequence:

```sql
CREATE SEQUENCE item_barcode_number_seq START WITH 1;
```

Keep:

```sql
barcode TEXT NOT NULL UNIQUE
```

Do not drop or rename existing columns.

### `app.py`

Add imports:

```python
import re
from urllib.parse import quote
import qrcode
```

For PNG generation:

```python
from io import BytesIO
```

The project already imports `io`, so `io.BytesIO()` can be used instead.

Add config:

```python
APP_BASE_URL = os.environ.get("APP_BASE_URL")
BARCODE_PREFIX = os.environ.get("BARCODE_PREFIX", "KATZ-NURS")
```

Add helper functions:

```python
def generate_next_item_barcode(db):
    number = db.execute("SELECT nextval('item_barcode_number_seq') AS number").fetchone()["number"]
    return f"{BARCODE_PREFIX}-{number:06d}"
```

Add helper:

```python
def get_item_by_barcode(db, barcode):
    return db.execute(
        """
        SELECT id, barcode, name, bin_location, room, company,
               quantity, minimum_quantity, location, expiration_date, notes
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()
```

Add helper:

```python
def build_item_stock_url(barcode):
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    return f"{base_url}{url_for('item_stock', barcode=barcode)}"
```

Add routes:

```text
/items/<barcode>
/items/<barcode>/label
/items/<barcode>/qr.png
/items/<barcode>/stock
```

Refactor stock transaction logic:

```text
Move common add/remove logic out of scan() into helper
Use it from scan() and item_stock()
```

### `templates/item_new.html`

Change barcode field behavior:

Current:

```text
Barcode required
```

New:

```text
Barcode optional
Helper text: Leave blank to auto-generate a Katz Nursing inventory code.
```

Possible UI:

```html
<label for="barcode">Barcode / Internal Code</label>
<input ... placeholder="Leave blank to auto-generate">
```

### `templates/items.html`

Add links:

```text
View
Print Label
Edit
```

For each item row:

```text
All Items table -> Action column:
View | Print Label | Edit
```

### `templates/item_detail.html`

New file.

Displays item details and buttons:

```text
Stock Action
Print Label
Edit Item
All Items
```

### `templates/item_label.html`

New file.

Displays printable QR label.

Should include:

```text
Katz Nursing Inventory
Item name
Barcode/internal code
QR image
Room
Bin
```

### `templates/item_stock.html`

New file.

Similar to `scan.html`, but item is already known.

Should not require user to type barcode.

### `static/css/styles.css`

Add label styles:

```css
.qr-label {
    background: white;
    border: 1px solid #111827;
    color: #111827;
    padding: 12px;
    width: 2.4in;
}

.qr-label img {
    height: 1.1in;
    width: 1.1in;
}

@media print {
    header,
    footer,
    nav,
    .no-print {
        display: none;
    }

    body {
        background: white;
    }

    section {
        border: 0;
        box-shadow: none;
        padding: 0;
    }
}
```

Do not over-polish printing in the first version. Test with the real printer later.

---

## Login Behavior For QR Scans

If a user scans a QR code and is not logged in, the app currently redirects to login.

This is secure.

Future improvement:

```text
Remember the page the user wanted
After login, redirect back to that QR stock page
```

Implementation idea:

In `require_login()`:

```python
return redirect(url_for("login", next=request.path))
```

In login route:

```python
next_url = request.args.get("next")
return redirect(next_url or url_for("dashboard"))
```

Security note:

Only allow local paths beginning with `/`.

Do not allow arbitrary external redirect URLs.

Initial QR feature can skip this improvement if we want to reduce risk.

---

## Camera Scanning Requirements

Phone camera scanning works only if the URL in the QR code is reachable by the phone.

### Local Computer Only

This will not work from phone:

```text
http://127.0.0.1:5001/items/KATZ-NURS-000014/stock
```

Because on the phone, `127.0.0.1` means the phone itself.

### Local Network Testing

Works if computer and phone are on same Wi-Fi:

```text
http://computer-ip-address:5001/items/KATZ-NURS-000014/stock
```

Example:

```text
http://192.168.1.25:5001/items/KATZ-NURS-000014/stock
```

Flask must run with:

```bash
python -m flask --app app run --host 0.0.0.0 --port 5001
```

Only use this on a trusted local network.

### Production

Best final QR URL:

```text
https://inventory.katz.yu.edu/items/KATZ-NURS-000014/stock
```

This requires cloud deployment first.

---

## Backward Compatibility Plan

Do not remove `/scan`.

Keep both workflows:

```text
Manual/USB scanner workflow: /scan
QR camera workflow: /items/<barcode>/stock
```

This is safer because:

- Existing barcode scanner workflow still works
- Users can still type a barcode manually
- QR workflow can be tested separately
- If QR label printing has issues, old scan page still works

Do not remove the barcode column.

Do not rename barcode field yet.

Do not require QR code for old items immediately.

---

## Recommended Implementation Order

### Step 1: Add Dependencies And Config

Files:

```text
requirements.txt
.env.example
app.py
```

Add:

```text
qrcode[pil]
APP_BASE_URL
BARCODE_PREFIX
```

Verify:

```bash
python -m py_compile app.py
```

### Step 2: Add Barcode Sequence

Files:

```text
schema.sql
app.py
```

Add:

```sql
CREATE SEQUENCE item_barcode_number_seq START WITH 1;
```

Also add runtime safety:

```python
CREATE SEQUENCE IF NOT EXISTS item_barcode_number_seq START WITH 1
```

This prevents errors if an existing database does not have the sequence yet.

### Step 3: Make Barcode Optional On Add Item

Files:

```text
app.py
templates/item_new.html
```

Behavior:

```text
If barcode field blank:
    generate internal barcode
If barcode field filled:
    use it
```

Verify:

```text
Create item with blank barcode
Confirm KATZ-NURS-000001 saved
Create item with manual barcode
Confirm manual barcode still works
```

### Step 4: Add Item Detail Page

Files:

```text
app.py
templates/item_detail.html
templates/items.html
```

Add:

```text
/items/<barcode>
```

Verify:

```text
All Items -> View opens correct item
Invalid barcode gives 404
Students can view
Faculty/admin can edit
```

### Step 5: Add QR PNG Route

Files:

```text
app.py
```

Add:

```text
/items/<barcode>/qr.png
```

Verify in browser:

```text
Open QR PNG URL
Image appears
Scan image with phone
Phone reads stock URL
```

### Step 6: Add Printable Label Page

Files:

```text
app.py
templates/item_label.html
static/css/styles.css
templates/items.html
templates/item_detail.html
```

Add:

```text
/items/<barcode>/label
```

Verify:

```text
Label page opens
QR image appears
Print button opens browser print
Printed label has item name, code, room, bin
```

### Step 7: Add QR Stock Page

Files:

```text
app.py
templates/item_stock.html
```

Add:

```text
/items/<barcode>/stock
```

Verify:

```text
Open stock URL
Item is prefilled
Add stock works
Remove stock works
Cannot remove more than available
Transaction history records user/date/time/instructor/topic/notes
```

### Step 8: Refactor Stock Logic Safely

Only after the QR stock page works, reduce duplication.

Move shared logic into:

```python
process_stock_transaction()
```

Both pages use it:

```text
/scan
/items/<barcode>/stock
```

Verify old scan page still works.

---

## Testing Checklist

### Item Creation Tests

- Add item with blank barcode.
- Confirm generated code format:

```text
KATZ-NURS-000001
```

- Add another item.
- Confirm number increments.
- Add item with manual barcode.
- Confirm manual barcode saves.
- Try duplicate barcode.
- Confirm duplicate is blocked.

### QR Image Tests

- Open QR image route.
- Confirm PNG loads.
- Scan QR with phone.
- Confirm URL points to correct item stock page.
- Confirm QR does not contain localhost in production.

### Label Tests

- Open label page.
- Confirm label displays:
  - Katz Nursing Inventory
  - Item name
  - Internal code
  - QR code
  - Room
  - Bin
- Click Print.
- Print to PDF first.
- Print to physical label printer second.

### QR Stock Tests

- Open stock page from QR.
- Add stock.
- Remove stock.
- Try removing too much.
- Leave required fields blank.
- Confirm validation prevents incomplete transactions.
- Confirm transaction history records correct item.

### Permission Tests

- Student can open QR stock page only if allowed by current workflow.
- Faculty can open and use stock page.
- Admin can open and use stock page.
- Faculty/admin can print labels.
- If students should not print labels, hide print buttons for students.

Recommended first rule:

```text
All logged-in users can stock items.
Faculty/admin can create/edit/print labels.
```

This matches the current system where logged-in users can access `/scan`.

### Regression Tests

Make sure these still work:

```text
Login
Dashboard
All Items
Low Stock Items
Add New Item
Edit Item
Scan Item
Transactions
Transaction filters
Transaction CSV export
Inventory CSV export
User management
Database status for admin only
```

---

## Safety Rules To Avoid Breaking The System

1. Do not remove the existing `/scan` page.
2. Do not remove the existing `barcode` column.
3. Do not force old items to change barcode immediately.
4. Do not store QR images in the database.
5. Do not require cloud deployment before local QR label testing.
6. Add new routes separately before changing existing workflows.
7. Use database sequence, not `COUNT(*) + 1`.
8. Add backend checks, not only template buttons.
9. Test with current demo accounts:

```text
A1001 admin
F1001 faculty
S1001 student
```

10. Test printing to PDF before physical label printer.

---

## Suggested Git Commit Plan

Commit in small pieces.

### Commit 1

```bash
git add requirements.txt .env.example schema.sql app.py
git commit -m "Add QR code configuration and barcode sequence"
```

### Commit 2

```bash
git add app.py templates/item_new.html
git commit -m "Auto-generate item barcodes"
```

### Commit 3

```bash
git add app.py templates/item_detail.html templates/items.html
git commit -m "Add item detail page"
```

### Commit 4

```bash
git add app.py templates/item_label.html static/css/styles.css
git commit -m "Add printable QR item labels"
```

### Commit 5

```bash
git add app.py templates/item_stock.html
git commit -m "Add QR-linked stock action page"
```

### Commit 6

```bash
git add app.py
git commit -m "Share stock transaction logic"
```

Push after each confirmed working step or after a tested group:

```bash
git push origin master
```

---

## Future Enhancements

After the first QR workflow is stable:

### Return To QR Page After Login

When a user scans QR while logged out:

```text
Scan QR -> login -> returns to item stock page
```

### Batch Label Printing

Allow printing many labels at once:

```text
Select items -> Print Labels
```

### Reprint Label Tracking

Track when a label was printed:

```text
printed_at
printed_by
```

### Inactive Items

Instead of deleting items:

```text
Mark item inactive
QR page shows item archived
```

### QR For Item Detail Instead Of Stock

Alternative:

```text
QR opens item detail page
Item detail page has Add Stock / Remove Stock buttons
```

This is slightly safer because scanning does not go directly to a transaction form.

Recommended for final product:

```text
QR opens item detail page
Detail page has Stock Action button
```

Recommended for faster workflow:

```text
QR opens stock action page directly
```

For this project, direct stock page is acceptable because that is the requested workflow.

---

## Recommended First Version

The first QR version should include only:

```text
Auto-generated KATZ-NURS code
QR PNG route
Printable label page
QR stock page
Keep old /scan page
```

Do not add:

```text
Batch printing
Label print history
Item archive
Complex printer integration
Mobile app
External QR service
```

Keep it simple first.

---

## Final Target Workflow

```text
Faculty/Admin logs in
Goes to Items -> Add New Item
Leaves barcode blank
Fills item details
Submits form
System creates KATZ-NURS-000014
System stores item in PostgreSQL
System opens printable QR label page
Faculty/Admin prints label
Label is pasted on item or bin

Later:
User scans QR code with camera
Browser opens /items/KATZ-NURS-000014/stock
System loads the item
User selects Add Stock or Remove Stock
User fills quantity, lab instructor, topic, notes
System updates quantity
System records transaction
Transaction appears in dashboard and transaction history
CSV exports include the transaction
```

This approach connects the physical university inventory item to the software record while keeping the database as the source of truth.

---

## Update: July 18, 2026 - QR Download and Multi-Label Printing

This update adds practical QR-code output options for users who need to work
with Brother P-touch Editor, Word, Pages, Google Docs, or browser-based printing.

### What Was Added

```text
1. Download raw QR PNG
   Route:
       /items/<barcode>/qr.png?download=1

   Purpose:
       Downloads only the QR image. This is useful when users want to paste the
       QR into P-touch Editor, Word, Pages, Google Docs, or another label tool.

2. Download QR + label PNG
   Route:
       /items/<barcode>/qr-label.png

   Purpose:
       Generates a single PNG image containing:
           - QR code
           - item barcode/internal code below it

       This avoids A4/browser print layout problems and gives users a simple
       image they can paste into label software.

3. Print Multiple QR Labels page
   Route:
       /items/<barcode>/label-sheet

   Purpose:
       Lets users choose:
           - number of copies,
           - QR size in millimeters,
           - spacing in millimeters,
           - label text.

       The page renders repeated QR labels and can be printed from the browser
       or saved as PDF.
```

### UI Entry Points

```text
Item Detail:
    - Download QR PNG
    - Download QR + Label PNG
    - Print Multiple QR Labels

Full Label Page:
    - Download QR PNG
    - Download QR + Label PNG
    - Print Multiple QR Labels

QR Only Label Page:
    - Download QR PNG
    - Download QR + Label PNG
    - Print Multiple QR Labels

All Items table:
    - Sheet
```

### Why

Browser printing can default to A4/PDF-style page layout and may not expose all
label-printer sizing options. Downloadable PNGs give users a reliable manual
path for P-touch Editor or document editors, while the label-sheet page supports
printing multiple copies at once.

### Safety / Permissions

```text
- These routes require the same faculty/administrator item-manager access as
  existing QR label routes.
- The QR code still points to the app's item stock page.
- The database remains the source of truth.
- No external QR-code service is used.
```

### Verification

```text
Tests verify:
    - raw QR PNG download returns PNG with a download filename,
    - QR + label PNG returns PNG with a download filename,
    - multiple-label sheet renders the requested copy count,
    - faculty can access the new QR output routes,
    - the old 00/00/0000 expiration sentinel does not appear.
```
