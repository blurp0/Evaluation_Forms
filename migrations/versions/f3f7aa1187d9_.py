"""empty message

Revision ID: f3f7aa1187d9
Revises: 3649919aa91e
Create Date: 2024-12-08 21:23:58.682926

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f3f7aa1187d9'
down_revision = '3649919aa91e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('form_distributions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('distribution_status', sa.Enum('pending', 'completed', 'missing', name='distribution_status'), nullable=False))
        batch_op.drop_column('status')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('form_distributions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', mysql.ENUM('pending', 'completed', 'missing'), nullable=False))
        batch_op.drop_column('distribution_status')

    # ### end Alembic commands ###