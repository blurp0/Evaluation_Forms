"""empty message

Revision ID: 55452be142a7
Revises: adec3f0bd8fb
Create Date: 2024-12-03 13:50:14.518932

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '55452be142a7'
down_revision = 'adec3f0bd8fb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('form_distributions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deadline', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.Enum('pending', 'completed', 'missing', name='distribution_status'), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('form_distributions', schema=None) as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('deadline')

    # ### end Alembic commands ###
