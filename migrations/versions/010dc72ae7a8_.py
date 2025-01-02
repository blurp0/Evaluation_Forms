"""empty message

Revision ID: 010dc72ae7a8
Revises: 57e3ce36868b
Create Date: 2024-11-26 15:33:01.528746

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '010dc72ae7a8'
down_revision = '57e3ce36868b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.drop_constraint('answers_ibfk_4', type_='foreignkey')
        batch_op.drop_column('question_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('question_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('answers_ibfk_4', 'questions', ['question_id'], ['id'])

    # ### end Alembic commands ###
