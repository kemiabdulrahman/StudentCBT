# Database Migration Guide

## Overview
This guide explains how to migrate your existing Student CBT Application database from the old Exam-based structure to the new Assessment-based structure.

## Important Changes

### Model Changes
1. **Exam → Assessment**: The `Exam` model has been renamed to `Assessment` for more generic usage
2. **Subject Code Removed**: The `code` field has been removed from the Subject model
3. **Result Visibility Control**: Added `show_results` boolean field to Assessment model
4. **Fill-in-the-Blank Support**: Added support for fill-in-the-blank questions
5. **Increased Field Sizes**:
   - `answer_text` increased from 10 to 200 characters
   - `correct_answer` increased from 10 to 200 characters

### Database Schema Changes
- `exams` table renamed to `assessments`
- `exam_id` foreign key columns renamed to `assessment_id` in:
  - `questions` table
  - `attempts` table
- `show_results` column added to `assessments` table
- `code` column removed from `subjects` table
- Unique constraint in `attempts` table updated

## Migration Steps

### Option 1: Fresh Installation (Recommended for Development)
If you don't have critical data to preserve:

```bash
# Backup existing database (optional)
cp instance/cbt_app.db instance/cbt_app.db.backup

# Remove old database
rm instance/cbt_app.db

# Initialize new database with updated schema
flask db init  # Only if migrations folder doesn't exist
flask db migrate -m "Initial assessment-based schema"
flask db upgrade
```

### Option 2: Migrate Existing Database
If you need to preserve existing data:

```bash
# Backup database first!
cp instance/cbt_app.db instance/cbt_app.db.backup

# Run the migration
flask db upgrade
```

**Note for SQLite Users**: SQLite has limitations with ALTER TABLE operations. If you encounter issues:

1. Use the provided migration script which uses batch operations for SQLite compatibility
2. Alternatively, manually migrate data:

```bash
# Export data from old database
python export_data.py  # You'll need to create this script

# Remove old database
rm instance/cbt_app.db

# Create new database with new schema
flask db upgrade

# Import data into new database
python import_data.py  # You'll need to create this script
```

### Option 3: Manual Database Update (For SQLite)
If automated migration fails, you can manually update the database:

```sql
-- Start a transaction
BEGIN TRANSACTION;

-- Rename exams table to assessments
ALTER TABLE exams RENAME TO assessments;

-- Add show_results column (SQLite version)
-- Note: SQLite doesn't support ADD COLUMN with DEFAULT in old versions
-- You may need to recreate the table

-- Update foreign keys (requires recreating tables in SQLite)
-- See detailed SQL script in migrations/manual_migration.sql

COMMIT;
```

## Verification

After migration, verify the changes:

```bash
# Check database schema
sqlite3 instance/cbt_app.db ".schema"

# Test the application
flask run
```

## New Features After Migration

### For Administrators:
1. **Assessment Management**: Create and manage assessments (formerly exams)
2. **Result Visibility Control**: Toggle whether students can view results immediately
3. **Export Functionality**:
   - Export assessment results to PDF
   - Export assessment results to Excel
   - Export individual student answer sheets
4. **Fill-in-the-Blank Questions**: Create fill-in-the-blank questions alongside MCQ and True/False

### For Students:
1. **Controlled Result Viewing**: View results only when administrator enables it
2. **Answer Sheet Export**: Download detailed answer sheets showing all questions and answers
3. **Fill-in-the-Blank Support**: Answer fill-in-the-blank questions with automatic grading

## Required Dependencies

Make sure to install new dependencies:

```bash
pip install -r requirements.txt
```

New packages added:
- `reportlab`: For PDF generation
- `email-validator`: For improved email validation

## Rollback

If you need to rollback to the previous version:

```bash
# Restore backup
cp instance/cbt_app.db.backup instance/cbt_app.db

# Or use Flask-Migrate downgrade
flask db downgrade
```

## Troubleshooting

### Issue: "Table already exists" error
- Delete the database and reinitialize: `rm instance/cbt_app.db && flask db upgrade`

### Issue: "Foreign key constraint failed"
- Ensure you backed up data before migration
- Use fresh installation option for development

### Issue: "Column doesn't exist" error
- Run `flask db upgrade` to apply all migrations
- Check that you're using the correct branch of the code

## Support

For issues or questions, please refer to the main README or create an issue in the repository.
