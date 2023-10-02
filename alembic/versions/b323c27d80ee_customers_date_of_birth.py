"""customers date_of_birth

Revision ID: b323c27d80ee
Revises: 8fe5543b3030
Create Date: 2023-07-10 18:24:44.431825

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b323c27d80ee'
down_revision = '8fe5543b3030'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE customers
        ADD COLUMN date_of_birth TIMESTAMP;
        """
    )

def downgrade():
    op.execute(
        """
        ALTER TABLE customers
        DROP COLUMN date_of_birth;
        """
    )
