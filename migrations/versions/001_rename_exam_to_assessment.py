"""Rename Exam to Assessment and add new features

Revision ID: 001_assessment_restructure
Revises:
Create Date: 2025-10-30

Changes:
- Rename exams table to assessments
- Add show_results column to assessments
- Remove code column from subjects
- Update foreign key column names from exam_id to assessment_id
- Increase answer_text size from 10 to 200 characters
- Increase correct_answer size from 10 to 200 characters
- Support for fill-in-the-blank questions

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_assessment_restructure'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Rename exams table to assessments
    op.rename_table('exams', 'assessments')

    # Step 2: Add show_results column to assessments
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('show_results', sa.Boolean(), nullable=True, server_default='0'))

    # Step 3: Update foreign key column names in questions table
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.alter_column('exam_id', new_column_name='assessment_id')
        batch_op.alter_column('correct_answer', type_=sa.String(length=200))

    # Step 4: Update foreign key column names in attempts table
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.drop_constraint('unique_student_exam_attempt', type_='unique')
        batch_op.alter_column('exam_id', new_column_name='assessment_id')
        batch_op.create_unique_constraint('unique_student_assessment_attempt', ['student_id', 'assessment_id'])

    # Step 5: Update answer_text column size in answers table
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.alter_column('answer_text', type_=sa.String(length=200))

    # Step 6: Remove code column from subjects table
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.drop_column('code')


def downgrade():
    # Reverse Step 6: Add back code column to subjects
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('code', sa.String(length=20), nullable=True))

    # Reverse Step 5: Restore answer_text column size
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.alter_column('answer_text', type_=sa.String(length=10))

    # Reverse Step 4: Restore foreign key column names in attempts table
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.drop_constraint('unique_student_assessment_attempt', type_='unique')
        batch_op.alter_column('assessment_id', new_column_name='exam_id')
        batch_op.create_unique_constraint('unique_student_exam_attempt', ['student_id', 'exam_id'])

    # Reverse Step 3: Restore foreign key column names in questions table
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.alter_column('assessment_id', new_column_name='exam_id')
        batch_op.alter_column('correct_answer', type_=sa.String(length=10))

    # Reverse Step 2: Remove show_results column
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_column('show_results')

    # Reverse Step 1: Rename assessments table back to exams
    op.rename_table('assessments', 'exams')
