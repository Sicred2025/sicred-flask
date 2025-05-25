"""add is_admin to user

Revision ID: 1234567890ab
Revises: 2b0cddc9a52e
Create Date: 2025-05-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = '2b0cddc9a52e'
branch_labels = None
depends_on = None

def upgrade():
    # Add is_admin column with default False
    op.add_column('user', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))

def downgrade():
    # Remove is_admin column
    op.drop_column('user', 'is_admin')
