"""empty message

Revision ID: 57e3ce36868b
Revises: 08acbaeab905
Create Date: 2024-11-26 15:29:34.060617

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '57e3ce36868b'
down_revision = '08acbaeab905'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('question_id', sa.Integer(), nullable=True))
        batch_op.alter_column('answer_value',
               existing_type=mysql.FLOAT(),
               type_=sa.Integer(),
               existing_nullable=True)
        batch_op.alter_column('comment',
               existing_type=mysql.VARCHAR(length=500),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.create_foreign_key(None, 'questions', ['question_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.alter_column('comment',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=500),
               existing_nullable=True)
        batch_op.alter_column('answer_value',
               existing_type=sa.Integer(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
        batch_op.drop_column('question_id')

    # ### end Alembic commands ###