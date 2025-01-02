"""empty message

Revision ID: 2daac4a8d820
Revises: f638b0e39b8e
Create Date: 2024-12-02 15:45:11.190088

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2daac4a8d820'
down_revision = 'f638b0e39b8e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('comment', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.drop_column('comment')

    # ### end Alembic commands ###