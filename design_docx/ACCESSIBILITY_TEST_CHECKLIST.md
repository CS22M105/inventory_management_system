# Accessibility Test Checklist

Date: July 10, 2026

Project: Katz Nursing School Inventory Management System

Target: WCAG 2.2 AA where practical.

## How To Use This Checklist

Run this checklist on staging before a university pilot and again before a
production launch. Record pass/fail notes and any fixes in `PROGRESS_REPORT.md`.

Recommended tools:

```text
Manual:
    Keyboard only
    VoiceOver on macOS or NVDA on Windows
    Browser zoom at 200%
    Phone/tablet browser

Automated:
    axe DevTools or equivalent browser accessibility checker
```

## Core Pages To Test

```text
[ ] Login
[ ] Forgot password
[ ] Reset password
[ ] Set password / invite link
[ ] Dashboard
[ ] Dashboard camera QR scanner
[ ] Items dropdown in navigation
[ ] All Items
[ ] Add New Item
[ ] Edit Item
[ ] Item Detail
[ ] Print QR Label
[ ] Scan Item manual form
[ ] Per-item Stock Action page
[ ] Low Stock Items
[ ] Transaction History filters
[ ] Transaction CSV export button
[ ] Manage Users
[ ] Add User
[ ] Database Status (administrator only)
```

## Keyboard Navigation

For each page:

```text
[ ] Tab order follows the visual order.
[ ] Shift+Tab moves backward correctly.
[ ] Enter activates links and buttons.
[ ] Space activates buttons and dropdown summaries where expected.
[ ] Focus is always visible.
[ ] No keyboard trap occurs.
[ ] Dropdown menus can be opened and closed using the keyboard.
[ ] Logout button is reachable.
[ ] CSV export buttons/links are reachable.
[ ] Camera Start/Stop buttons are reachable.
```

## Focus Visibility

```text
[ ] Links show a visible focus outline.
[ ] Buttons show a visible focus outline.
[ ] Form fields show a visible focus outline.
[ ] Navigation dropdown summary shows a visible focus outline.
[ ] Focus outline is not hidden behind layout elements.
[ ] Focus outline has enough contrast against the background.
```

## Forms

```text
[ ] Every input/select/textarea has a visible label.
[ ] Required fields are explained near the form.
[ ] Server-side errors are announced as alerts.
[ ] Client-side scan form errors are announced as alerts.
[ ] Invalid scan form fields set aria-invalid while highlighted.
[ ] Password show/hide buttons have accessible names.
[ ] Password show/hide buttons update pressed state.
[ ] Forms can be submitted without a mouse.
[ ] Error text explains what the user should fix.
```

## Tables And Reports

```text
[ ] Tables have clear column headers.
[ ] Transaction filters are labeled.
[ ] Pagination is reachable by keyboard.
[ ] Pagination has a navigation label.
[ ] Disabled pagination controls are communicated visually and with aria-disabled.
[ ] CSV export links/buttons are reachable and understandable.
```

## Camera QR Scanner

```text
[ ] Start Camera button is reachable by keyboard.
[ ] Stop Camera button is reachable by keyboard.
[ ] Camera status updates are announced through a live region.
[ ] Camera preview region has an accessible name.
[ ] Start Camera exposes expanded state.
[ ] Failure message explains manual fallback through Items > Scan Item.
[ ] Scanner does not create a keyboard trap.
[ ] Manual barcode entry remains available if camera access fails.
```

## Color And Visual Contrast

```text
[ ] Body text has sufficient contrast.
[ ] Navigation text has sufficient contrast.
[ ] Button text has sufficient contrast.
[ ] Error/success/warning messages have sufficient contrast.
[ ] Low-stock state does not rely only on color.
[ ] Focus outline has sufficient contrast.
[ ] Page is usable at 200% browser zoom.
```

## Screen Reader Checks

Using VoiceOver or NVDA:

```text
[ ] Page title identifies the current page.
[ ] Main landmark is discoverable.
[ ] Primary navigation landmark is discoverable.
[ ] Skip link moves to main content.
[ ] Form labels are announced.
[ ] Error messages are announced.
[ ] Password toggle buttons are announced clearly.
[ ] Camera scanner status updates are announced.
[ ] QR label image has useful alternate text.
[ ] Table headers are announced with cell values.
```

## Mobile / Responsive Checks

```text
[ ] Navigation wraps without overlapping text.
[ ] Forms fit on a phone viewport.
[ ] Buttons remain large enough to tap.
[ ] Camera controls remain visible and usable.
[ ] Transaction filters are usable on phone/tablet.
[ ] Text does not overlap or disappear.
```

## Acceptance Criteria

```text
[ ] No keyboard traps.
[ ] All critical workflows are usable without a mouse.
[ ] No critical automated accessibility violations remain.
[ ] No critical color-contrast failures remain.
[ ] Login, item creation, stock action, transaction filters, and user management
    are usable with a screen reader.
[ ] Known limitations are documented in ACCESSIBILITY_STATEMENT.md.
```
