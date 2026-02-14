"""drop questions_asked_weekly table

Revision ID: f6ea1da72c43
Revises: 29edcfec6201
Create Date: 2026-02-14 09:46:08.766398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6ea1da72c43'
down_revision: Union[str, Sequence[str], None] = '29edcfec6201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('questions_asked_weekly')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('questions_asked_weekly',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('class_name', sa.String(), nullable=True),
    sa.Column('subject', sa.String(), nullable=True),
    sa.Column('no_of_questions', sa.Integer(), nullable=True),
    sa.Column('week_start', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('class_name', 'subject', 'week_start', name='uix_question_weekly')
    )
    op.create_index(op.f('ix_questions_asked_weekly_class_name'), 'questions_asked_weekly', ['class_name'], unique=False)
    op.create_index(op.f('ix_questions_asked_weekly_subject'), 'questions_asked_weekly', ['subject'], unique=False)
