"""empty message

Revision ID: adec3f0bd8fb
Revises: 3ea3e1e7d931
Create Date: 2024-12-02 17:26:34.038227

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'adec3f0bd8fb'
down_revision = '3ea3e1e7d931'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('category_raw_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('comment', sa.Text(), nullable=True))
        batch_op.alter_column('raw_answer_value',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('category_raw_answers', schema=None) as batch_op:
        batch_op.alter_column('raw_answer_value',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
        batch_op.drop_column('comment')

    # ### end Alembic commands ###
