"""empty message

Revision ID: 117355f71699
Revises: e76c7eb07cb4
Create Date: 2024-12-08 17:34:52.743374

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '117355f71699'
down_revision = 'e76c7eb07cb4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(None, 'question_categories', ['category_id'], ['id'])
        batch_op.drop_column('category_name')

    with op.batch_alter_table('professors', schema=None) as batch_op:
        batch_op.drop_column('category_performance')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('professors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_performance', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True))

    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_name', mysql.VARCHAR(length=100), nullable=False))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('category_id')

    # ### end Alembic commands ###
