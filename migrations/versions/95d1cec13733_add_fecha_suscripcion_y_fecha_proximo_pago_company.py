"""add fecha_suscripcion y fecha_proximo_pago a Company

Revision ID: 95d1cec13733
Revises: 
Create Date: 2024-05-10

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('company', sa.Column('fecha_suscripcion', sa.DateTime(), nullable=True))
    op.add_column('company', sa.Column('fecha_proximo_pago', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('company', 'fecha_suscripcion')
    op.drop_column('company', 'fecha_proximo_pago') 