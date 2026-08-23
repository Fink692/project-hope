# Move your contacts into Project Hope

You do not need technical experience to move a contact list. Project Hope accepts a normal Excel or CSV spreadsheet, checks it without changing anything, and lets you review every row before the import begins.

Only an organization owner or administrator can import, export, or merge contacts. Coordinators and staff can add and correct individual contacts. Viewers cannot change records.

## Before you begin

1. Export the contacts from your current system as an `.xlsx`, `.csv`, or `.tsv` file.
2. Keep that original export somewhere safe. Do not edit your only copy.
3. Remove columns your team does not need to bring into Project Hope.
4. If the file is an older `.xls` workbook, open it in your spreadsheet app and save it as `.xlsx`.

A file can contain up to 2,500 contact rows, 50 columns, and 5 MB by default. A setup partner can change those limits for a larger approved migration.

## The simplest path

1. Sign in and open **CRM**.
2. Choose **Import & export**.
3. If you are starting a new sheet, choose **Excel template**. It includes instructions and dropdowns.
4. Under **Contact file**, choose your spreadsheet.
5. Choose **Preview contact file**.

Previewing does not create, edit, or remove contacts. The preview is private, is tied to your account and organization, and expires after about 15 minutes.

## Review the preview

Project Hope puts every row into one of four groups:

- **Ready to add:** no likely existing contact was found. The suggested action is **Add as a new contact**.
- **Existing match:** the email or external reference matches an active contact. The safe default is **Skip this row**.
- **Possible duplicate:** the name, organization, or name and phone may match. The safe default is **Skip this row**.
- **Needs correction:** the row has an invalid value, a repeated email/reference in the same file, a spreadsheet formula, or no useful identity information. It cannot be imported yet.

For an existing or possible match, you may choose **Fill missing details on…**. This fills blank contact details only. It does not overwrite an existing name, email, phone, or reference. Imported notes are appended, and a stricter sensitivity or consent status is preserved.

If a row needs correction:

1. Keep the Project Hope preview open.
2. Correct that row in your original spreadsheet.
3. Save the file.
4. Choose the corrected file and preview it again.

When the review looks right, choose **Import reviewed rows**. Project Hope checks the same file again before it saves anything. The completion message says exactly how many records were added, filled in, unchanged, skipped, or invalid.

## Clean up possible duplicates

Open **Find duplicates** in CRM after the import. Project Hope checks exact email and external references, plus stronger or possible name-based matches.

For each pair:

1. Compare both records.
2. Choose which contact should remain active.
3. Read the merge explanation.
4. Select the confirmation box.
5. Choose **Merge reviewed pair**.

A merge does not erase the source contact. Project Hope marks it as merged, points it to the active contact, combines blank details and notes safely, and moves linked operational history. A merge stops if contacts are under legal hold or both records have volunteer profiles that require a person to resolve them first.

## Export a copy

An owner or administrator can choose **Export Excel** or **Export CSV** at any time. The export contains active contacts and Project Hope record identifiers. Formula-like text is written safely so opening a CSV cannot turn a contact note into a spreadsheet command.

An export is a portable copy of contact data. It is not a complete system backup. Your setup partner should also run and test the encrypted database backup and restore process in the [production deployment guide](operations/production-deployment.md).

## What Project Hope protects

- Imports are restricted to the organization you are signed into.
- A preview token cannot be reused by another user, organization, or changed file.
- Modern Excel files are checked for unsafe archive paths, macros, external workbook links, excessive expansion, and formulas.
- The uploaded spreadsheet is parsed for the request; Project Hope does not keep a separate server-side copy of the preview file.
- Import and merge audit events contain counts and record identifiers, not spreadsheet rows or contact email addresses.
- Contact exports and migration responses are marked private and non-cacheable.
- Viewer accounts cannot create, edit, import, export, or merge contacts.

## If something does not work

- **No supported contact columns were found:** download the template and copy your data under its headings. Common headings such as “First Name,” “Email Address,” and “Phone Number” are recognized.
- **The preview expired:** choose **Preview contact file** again and repeat the review.
- **The file changed after preview:** preview the newly saved file again. This is an intentional safety check.
- **A formula was found:** replace it with the reviewed text value displayed by your spreadsheet app.
- **A merge is blocked:** check the message. Legal holds and two volunteer profiles require an administrator to resolve the underlying records first.
- **The file is too large:** split it into smaller files or ask the setup partner to approve and configure a larger limit.

If a problem remains, stop before importing and send the setup partner the error message, file type, and row number. Do not email them a spreadsheet containing personal information unless your organization has approved that support channel.
