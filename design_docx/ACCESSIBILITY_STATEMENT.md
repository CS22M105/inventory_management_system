# Accessibility Statement

Date: July 10, 2026

Project: Katz Nursing School Inventory Management System

## Commitment

The Katz Nursing School Inventory Management System is intended for university
users, including students, faculty, administrators, and staff who may use
keyboard navigation, screen readers, zoom, mobile devices, or other assistive
technology.

The project target is:

```text
WCAG 2.2 AA where practical.
```

## Current Accessibility Support

The application currently includes:

```text
- Semantic page structure with header, navigation, main content, and footer.
- Keyboard-focus styles for links, buttons, dropdown summaries, and form fields.
- Explicit labels for form fields.
- Password show/hide buttons with accessible names and pressed state.
- Error messages marked as alerts where they are rendered by the server.
- Success/status messages marked for assistive technology.
- Camera scanner status text announced through a live status region.
- Camera scanner controls that expose expanded/controlled state.
- Transaction pagination with a navigation label.
- QR label images with descriptive alt text.
```

## Known Limitations

These items still need verification before a university-wide production launch:

```text
- Full WCAG 2.2 AA audit has not yet been completed by an accessibility
  specialist.
- Automated axe/Deque-style browser scan has not yet been run on every page.
- VoiceOver/NVDA screen-reader testing still needs to be completed and recorded.
- Mobile screen-reader testing still needs to be completed.
- Camera permission prompts are browser-controlled and may vary by device.
- The third-party QR camera scanner library may have accessibility limitations
  outside this app's direct control.
```

## Recommended Verification Before Launch

Before a real university pilot:

```text
1. Complete the checklist in design_docx/ACCESSIBILITY_TEST_CHECKLIST.md.
2. Test all core workflows with keyboard only.
3. Test with VoiceOver on macOS or NVDA on Windows.
4. Run an automated browser accessibility checker such as axe DevTools.
5. Record findings and fixes in PROGRESS_REPORT.md.
6. Keep any unresolved limitations listed in this statement.
```

## Contact / Feedback

For a production deployment, replace this section with the university or product
support contact:

```text
Accessibility feedback contact: <support email or helpdesk URL>
Expected response time: <support policy>
```
