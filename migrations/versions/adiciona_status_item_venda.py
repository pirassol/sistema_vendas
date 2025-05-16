"""adiciona status item venda

Revision ID: adiciona_status_item_venda
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'adiciona_status_item_venda'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Adiciona a coluna status à tabela item_venda
    op.add_column('item_venda', sa.Column('status', sa.String(20), nullable=False, server_default='ativo'))

def downgrade():
    # Remove a coluna status da tabela item_venda
    op.drop_column('item_venda', 'status') 