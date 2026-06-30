# Proposal: Barcode-Based Inventory Management System for Nursing Education and Healthcare Settings

## 1. Project Overview

Manual inventory management is still common in nursing academic programs, simulation labs, medication rooms, hospitals, and healthcare-related organizations. Many teams rely on paper notes, handwritten sign-out sheets, or Excel spreadsheets to track supplies. This process is time-consuming, prone to human error, difficult to audit, and often does not provide real-time visibility into current stock levels.

This project proposes a low-cost, barcode-based inventory management system designed specifically for nursing education and healthcare training environments. The system will allow authorized users, such as students, faculty, lab coordinators, and staff, to log in using their student or faculty ID, scan item barcodes, and automatically update inventory records when items are added, removed, or restocked.

The goal is to create a practical, affordable software solution that can run on minimal-cost hardware while replacing manual Excel-based tracking with a more accurate and automated workflow.

## 2. Problem Statement

Current inventory workflows in many nursing and healthcare education environments involve:

- Manual entry of supply usage into Excel sheets.
- Delayed updates when items are removed or added.
- Difficulty identifying who used specific items and when.
- Frequent counting errors and missing stock information.
- Limited visibility into low-stock or frequently used items.
- Extra workload for faculty, staff, and lab coordinators.

These challenges can lead to supply shortages, wasted time, inaccurate records, and difficulty preparing for classes, simulations, clinical skills practice, and medication-room activities.

## 3. Proposed Solution

The proposed system will function similarly to a grocery-store checkout process, but adapted for nursing supplies and medication-room inventory. Each item type will receive a unique barcode. When users add or remove items, they will scan the barcode, enter the quantity, and submit the transaction. The system will automatically update the inventory database and maintain a clear activity log.

The end product will be a lightweight software application that can run on affordable hardware such as:

- A basic laptop or desktop computer.
- A tablet or low-cost touchscreen device.
- A USB barcode scanner or mobile-camera barcode scanner.
- A local database with optional Excel/CSV export.

## 4. Project Objectives

The main objectives are to:

- Replace manual spreadsheet-based inventory tracking with automated barcode scanning.
- Allow students, faculty, and staff to log in using institutional IDs.
- Track item additions, removals, and restocking activities in real time.
- Maintain an accurate database of available inventory.
- Generate exportable reports for auditing, planning, and supply ordering.
- Support low-cost implementation using readily available hardware.
- Build a clear prototype or minimum viable product by July 20, 2026.

## 5. Target Users

The system is intended for:

- Nursing students using supplies for practice or simulation.
- Faculty members supervising lab or medication-room activities.
- Simulation lab staff managing equipment and consumables.
- Inventory or administrative staff responsible for restocking.
- Healthcare training organizations that need simple supply tracking.

## 6. Core Features

### 6.1 User Login

Users will log in using a student ID, faculty ID, or staff ID. The system will record the user associated with each inventory transaction.

Recommended user roles:

- **Student:** Can check out or return approved items.
- **Faculty/Staff:** Can add items, remove items, adjust quantities, and review logs.
- **Administrator:** Can manage users, item records, reports, and system settings.

### 6.2 Item Registration

Authorized users can add new item types to the system. Each item record should include:

- Item name.
- Category, such as medication-room supply, simulation supply, PPE, wound care, or equipment.
- Barcode number.
- Unit of measurement, such as pieces, boxes, packets, bottles, or kits.
- Current quantity.
- Minimum stock threshold.
- Location, such as medication room, skills lab, storage room, or simulation lab.
- Optional notes, expiration date, or supplier information.

### 6.3 Barcode Scanning

Each item type will be assigned a barcode. Users can scan the barcode when:

- Adding new stock.
- Removing items from inventory.
- Returning unused items.
- Checking current item details.

The barcode scan will identify the item automatically and reduce manual typing.

### 6.4 Quantity Updates

After scanning an item, the user will enter the quantity being added or removed. The system will update the inventory count immediately and store the transaction in the activity log.

Example transactions:

- Add 20 boxes of gloves.
- Remove 5 IV start kits.
- Return 2 unused dressing packs.
- Adjust item count after a physical inventory check.

### 6.5 Automated Database and Spreadsheet Updates

The system will maintain a database as the primary source of truth. Excel or CSV reports can be generated automatically when needed.

This avoids the risk of multiple people manually editing the same spreadsheet while still allowing staff to download familiar spreadsheet-style reports.

### 6.6 Inventory Dashboard

The dashboard should show:

- Total inventory items.
- Low-stock items.
- Recent transactions.
- Most frequently used items.
- Items nearing expiration, if expiration tracking is included.
- Search and filter options by name, category, barcode, or location.

### 6.7 Reporting

Reports should support:

- Current stock levels.
- Usage history by date range.
- Transactions by user.
- Low-stock report.
- Restocking needs.
- Export to Excel or CSV.

## 7. Suggested System Workflow

### 7.1 Removing an Item

1. User logs in using student, faculty, or staff ID.
2. User selects "Remove Item."
3. User scans the item barcode.
4. System displays the item name and available quantity.
5. User enters the quantity being removed.
6. System updates inventory and records the transaction.

### 7.2 Adding or Restocking an Item

1. Authorized user logs in.
2. User selects "Add Stock."
3. User scans the barcode or searches for the item.
4. User enters the quantity being added.
5. System updates the database.
6. System records the date, time, user, item, and quantity.

### 7.3 Registering a New Item

1. Faculty, staff, or administrator logs in.
2. User selects "New Item."
3. User enters item details.
4. System assigns or records a barcode.
5. Barcode label can be printed and attached to the item shelf, bin, or package.

## 8. Minimum Viable Product Scope

For the first version, the system should focus on the essential functions needed to demonstrate value by July 20, 2026.

Recommended MVP features:

- Login using a user ID.
- Add new item records.
- Assign or enter barcode values.
- Scan barcode to find an item.
- Add stock quantity.
- Remove stock quantity.
- Maintain transaction history.
- Show current inventory table.
- Export inventory or transaction records to CSV/Excel.
- Display low-stock warnings.

Features that can be added after the MVP:

- Expiration-date alerts.
- Supplier management.
- Purchase-order generation.
- Email notifications.
- Integration with institutional login systems.
- Multi-room or multi-campus inventory tracking.
- Mobile app version.
- Advanced analytics dashboard.

## 9. Recommended Technical Approach

The system can be built as a lightweight web application that runs locally on a small computer or on an internal network.

Recommended software structure:

- **Frontend:** Simple web interface for login, scanning, item management, inventory table, and reports.
- **Backend:** Application server that handles user actions, barcode lookups, inventory updates, and reports.
- **Database:** PostgreSQL, a free and open-source relational database suitable for both local prototyping and production deployment.
- **Barcode scanner:** USB barcode scanner acting like a keyboard input, or a camera-based scanner for tablets.
- **Export:** CSV and Excel-compatible reports.

This approach keeps the project affordable while still allowing future expansion.

## 10. Data to Track

The database should include the following core records:

### Users

- User ID.
- Name.
- Role.
- Department or program.
- Active/inactive status.

### Items

- Item ID.
- Barcode.
- Item name.
- Category.
- Unit type.
- Current quantity.
- Minimum stock quantity.
- Location.
- Expiration date, if applicable.
- Notes.

### Transactions

- Transaction ID.
- User ID.
- Item ID.
- Transaction type: added, removed, returned, adjusted.
- Quantity.
- Date and time.
- Notes or reason, if needed.

## 11. Security and Accountability

Because this system may be used in medication-room or healthcare training environments, it should include basic accountability features:

- Login required before any inventory action.
- Role-based permissions for students, faculty, staff, and administrators.
- Transaction history that cannot be casually deleted by regular users.
- Clear record of who added or removed each item.
- Optional administrator review for manual quantity adjustments.

For the MVP, the system should be treated as an educational or training inventory tool unless additional compliance requirements are formally defined.

## 12. Timeline

Deadline: **July 20, 2026**

The timeline below assumes work begins immediately and focuses on delivering a working prototype by the deadline.

| Phase | Dates | Deliverables |
|---|---:|---|
| Phase 1: Requirements and Design | June 11 - June 16 | Finalize item categories, user roles, workflow, database fields, and hardware assumptions |
| Phase 2: Prototype Setup | June 17 - June 23 | Create application structure, database, login screen, and basic inventory table |
| Phase 3: Barcode and Inventory Workflow | June 24 - July 1 | Implement barcode lookup, add stock, remove stock, and transaction logging |
| Phase 4: Reports and Dashboard | July 2 - July 8 | Add low-stock view, recent activity, inventory reports, and CSV/Excel export |
| Phase 5: Testing and Refinement | July 9 - July 15 | Test with sample nursing supplies, fix errors, improve usability, and validate workflows |
| Phase 6: Final Proposal and Demo Preparation | July 16 - July 20 | Prepare demo, documentation, final proposal, and presentation-ready summary |

## 13. Expected Benefits

The completed system is expected to:

- Reduce manual data entry.
- Improve inventory accuracy.
- Save time for faculty and staff.
- Create accountability for supply usage.
- Help prevent unexpected supply shortages.
- Make restocking decisions easier.
- Provide professional reports for planning and auditing.
- Offer a scalable foundation for future healthcare inventory automation.

## 14. Cost Considerations

The project is designed to minimize cost by using:

- Existing computers or tablets when available.
- A low-cost USB barcode scanner.
- Barcode labels that can be printed using standard label sheets or a small label printer.
- Open-source or low-cost software tools.
- Local database storage for the first version.

Estimated hardware options:

| Item | Low-Cost Option |
|---|---:|
| Computer or tablet | Existing device if available |
| USB barcode scanner | Approximately $20-$50 |
| Barcode labels | Standard printable labels or label printer |
| Database | PostgreSQL, free and open source, no license cost |
| Software hosting | Local machine or internal network |

## 15. Risks and Mitigation

| Risk | Mitigation |
|---|---|
| Users forget to scan items | Keep scanning workflow simple and place scanner near supplies |
| Barcode labels become damaged | Print backup labels and attach barcodes to shelves or bins |
| Inventory count becomes inaccurate | Include periodic physical count and adjustment workflow |
| Staff need Excel reports | Provide CSV/Excel export rather than removing spreadsheet access completely |
| Scope becomes too large before July 20 | Focus first on MVP features and defer advanced integrations |
| Medication-related compliance is unclear | Position MVP as an educational inventory system until formal compliance rules are reviewed |

## 16. Success Criteria

The project will be considered successful if, by July 20, 2026:

- A user can log in using an ID.
- A new item can be registered with a barcode.
- An item can be scanned and identified by the system.
- Inventory quantities can be increased or decreased.
- The database updates automatically after each transaction.
- A transaction log records user, item, quantity, date, and action.
- Current inventory can be exported to CSV or Excel format.
- The system can be demonstrated using realistic nursing or medication-room supplies.

## 17. Future Expansion

After the initial prototype, the system can be expanded to include:

- Integration with institutional single sign-on.
- Cloud synchronization.
- Mobile barcode scanning.
- QR code support.
- Expiration-date monitoring.
- Automated reorder suggestions.
- Role-specific dashboards.
- Multi-location inventory tracking.
- Audit reports for administrators.
- Integration with purchasing systems.

## 18. Conclusion

This project proposes a practical and affordable inventory management system for nursing education and healthcare-related environments. By using barcode scanning, user login, automated database updates, and exportable reports, the system can significantly reduce manual spreadsheet work and improve accuracy, accountability, and supply readiness.

The recommended first step is to build a focused MVP by July 20, 2026. This MVP should demonstrate the complete core workflow: logging in, scanning an item, adding or removing quantities, updating inventory automatically, and producing reports. Once the prototype is validated, the system can be expanded into a more robust platform for broader academic, simulation, and healthcare inventory use.
