# System Diagrams: Nursing Inventory Management System

## Purpose of This File

This file contains visual diagrams for the inventory management system.

The goal is to understand the system from different design angles:

- What parts the system has.
- How the parts communicate.
- What data the system stores.
- What objects or classes may exist in code.
- How users move through important workflows.

The diagrams are written using Mermaid syntax. Mermaid lets us create diagrams inside Markdown files.

## 1. System Context Diagram

This diagram shows the system from the outside.

```mermaid
flowchart LR
    Student[Student]
    Faculty[Faculty or Staff]
    Admin[Administrator]
    Scanner[Barcode Scanner]
    System[Nursing Inventory System]
    Database[(SQLite Database)]
    Reports[CSV or Excel Reports]

    Student --> System
    Faculty --> System
    Admin --> System
    Scanner --> System
    System --> Database
    System --> Reports
```

Why this diagram matters:

It shows who or what interacts with the system. The main outside actors are users and the barcode scanner. The system stores data in SQLite and later produces reports.

## 2. High-Level Architecture Diagram

This diagram shows the main technical layers.

```mermaid
flowchart TB
    Browser[Web Browser]
    Flask[Flask Web Application]
    Templates[HTML Templates]
    Static[CSS and JavaScript Files]
    SQLite[(SQLite Database)]

    Browser --> Flask
    Flask --> Templates
    Flask --> Static
    Flask --> SQLite
    SQLite --> Flask
    Flask --> Browser
```

Why this diagram matters:

It shows how the browser, Flask app, HTML templates, static files, and database work together.

## 3. Entity Relationship Diagram

This diagram shows the database relationships.

```mermaid
erDiagram
    USERS ||--o{ TRANSACTIONS : performs
    ITEMS ||--o{ TRANSACTIONS : appears_in

    USERS {
        integer id PK
        text institution_id
        text name
        text role
        text department
        integer is_active
    }

    ITEMS {
        integer id PK
        text barcode
        text name
        text category
        text unit
        integer quantity
        integer minimum_quantity
        text location
        text expiration_date
        text notes
    }

    TRANSACTIONS {
        integer id PK
        integer user_id FK
        integer item_id FK
        text transaction_type
        integer quantity
        text created_at
        text notes
    }
```

Why this diagram matters:

It shows that one user can perform many transactions, and one item can appear in many transactions.

The `items` table stores the current inventory count. The `transactions` table stores the history of inventory changes.

## 4. Class Diagram

This diagram shows possible backend classes or concepts we may use as the code grows.

```mermaid
classDiagram
    class User {
        +int id
        +string institution_id
        +string name
        +string role
        +string department
        +bool is_active
        +can_manage_items()
    }

    class Item {
        +int id
        +string barcode
        +string name
        +string category
        +string unit
        +int quantity
        +int minimum_quantity
        +string location
        +string expiration_date
        +string notes
        +is_low_stock()
    }

    class Transaction {
        +int id
        +int user_id
        +int item_id
        +string transaction_type
        +int quantity
        +string created_at
        +string notes
    }

    class InventoryService {
        +find_item_by_barcode(barcode)
        +add_stock(user, item, quantity)
        +remove_stock(user, item, quantity)
        +create_transaction(user, item, type, quantity)
    }

    User "1" --> "many" Transaction
    Item "1" --> "many" Transaction
    InventoryService --> User
    InventoryService --> Item
    InventoryService --> Transaction
```

Why this diagram matters:

Even though the first Flask version may start with simple functions, this diagram helps us understand the main code responsibilities.

The `InventoryService` is a possible future layer that keeps inventory rules in one place.

## 5. Login Sequence Diagram

This diagram shows what happens when a user logs in.

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant FlaskApp as Flask App
    participant Database as SQLite Database

    User->>Browser: Enter institutional ID
    Browser->>FlaskApp: Submit login form
    FlaskApp->>Database: Find active user by institutional ID
    Database-->>FlaskApp: Return user record
    FlaskApp->>FlaskApp: Store user ID in session
    FlaskApp-->>Browser: Redirect to dashboard
    Browser-->>User: Show dashboard
```

Why this diagram matters:

It shows that login is not only a page. It is a flow involving the browser, Flask app, database, and session.

## 6. Add New Item Sequence Diagram

This diagram shows how an item is added to the system.

```mermaid
sequenceDiagram
    actor Staff as Faculty or Staff
    participant Browser
    participant FlaskApp as Flask App
    participant Database as SQLite Database

    Staff->>Browser: Open Add Item page
    Browser->>FlaskApp: Request item form
    FlaskApp-->>Browser: Show form
    Staff->>Browser: Enter item details and barcode
    Browser->>FlaskApp: Submit item form
    FlaskApp->>FlaskApp: Validate required fields
    FlaskApp->>Database: Insert item record
    Database-->>FlaskApp: Confirm saved item
    FlaskApp-->>Browser: Redirect to inventory list
    Browser-->>Staff: Show new item in inventory
```

Why this diagram matters:

It shows that an item must be saved in the database before barcode scanning can find it later.

## 7. Remove Stock Sequence Diagram

This diagram shows the main barcode usage flow for removing inventory.

```mermaid
sequenceDiagram
    actor User
    participant Scanner as Barcode Scanner
    participant Browser
    participant FlaskApp as Flask App
    participant Database as SQLite Database

    User->>Browser: Click barcode input
    User->>Scanner: Scan item barcode
    Scanner->>Browser: Type barcode value
    Browser->>FlaskApp: Submit barcode and quantity
    FlaskApp->>Database: Find item by barcode
    Database-->>FlaskApp: Return item record
    FlaskApp->>FlaskApp: Check available quantity
    FlaskApp->>Database: Decrease item quantity
    FlaskApp->>Database: Insert transaction record
    FlaskApp-->>Browser: Show updated inventory result
    Browser-->>User: Confirm item was removed
```

Why this diagram matters:

This is one of the most important system flows. It shows how scanning an item leads to an automatic database update and transaction record.

## 8. Add Stock Sequence Diagram

This diagram shows how restocking works.

```mermaid
sequenceDiagram
    actor Staff as Faculty or Staff
    participant Scanner as Barcode Scanner
    participant Browser
    participant FlaskApp as Flask App
    participant Database as SQLite Database

    Staff->>Browser: Open scan or add stock page
    Staff->>Scanner: Scan item barcode
    Scanner->>Browser: Type barcode value
    Staff->>Browser: Enter quantity added
    Browser->>FlaskApp: Submit barcode and quantity
    FlaskApp->>Database: Find item by barcode
    Database-->>FlaskApp: Return item record
    FlaskApp->>Database: Increase item quantity
    FlaskApp->>Database: Insert transaction record
    FlaskApp-->>Browser: Show updated item quantity
```

Why this diagram matters:

It shows that adding stock and removing stock are similar flows. The main difference is whether quantity increases or decreases.

## 9. Activity Diagram: Inventory Action

This diagram shows the decision path for adding or removing inventory.

```mermaid
flowchart TD
    Start([Start])
    Login{User logged in?}
    Scan[Scan or enter barcode]
    Found{Item found?}
    Action{Add or remove?}
    Add[Increase item quantity]
    RemoveCheck{Enough quantity available?}
    Remove[Decrease item quantity]
    Transaction[Create transaction record]
    Error[Show error message]
    End([End])

    Start --> Login
    Login -- No --> Error --> End
    Login -- Yes --> Scan
    Scan --> Found
    Found -- No --> Error
    Found -- Yes --> Action
    Action -- Add --> Add --> Transaction --> End
    Action -- Remove --> RemoveCheck
    RemoveCheck -- No --> Error
    RemoveCheck -- Yes --> Remove --> Transaction --> End
```

Why this diagram matters:

It shows important decision points, such as whether a user is logged in, whether the barcode exists, and whether enough quantity is available before removing stock.

## 10. Deployment Diagram for MVP

This diagram shows the first low-cost deployment idea.

```mermaid
flowchart LR
    Device[Low-Cost Laptop or Desktop]
    Browser[Browser on Same Device]
    App[Local Flask App]
    DB[(Local SQLite File)]
    Scanner[USB Barcode Scanner]

    Scanner --> Browser
    Browser --> App
    App --> DB
    Device --- Browser
    Device --- App
    Device --- DB
```

Why this diagram matters:

The MVP can run on one local machine. This keeps cost and setup complexity low.

## 11. Future Deployment Diagram

This diagram shows a possible future version if the system grows.

```mermaid
flowchart LR
    User1[Lab Computer]
    User2[Faculty Laptop]
    User3[Tablet]
    WebServer[Hosted Web Application]
    Database[(PostgreSQL or MySQL Database)]
    Reports[Reports and Exports]

    User1 --> WebServer
    User2 --> WebServer
    User3 --> WebServer
    WebServer --> Database
    WebServer --> Reports
```

Why this diagram matters:

This shows how the system could later support multiple devices, a hosted application, and a stronger database.

## Summary

These diagrams help us understand the system before adding more code.

The most important diagrams for the first build are:

- Entity relationship diagram.
- Login sequence diagram.
- Add item sequence diagram.
- Add stock sequence diagram.
- Remove stock sequence diagram.

These directly match the first database tables and the core MVP workflows.
