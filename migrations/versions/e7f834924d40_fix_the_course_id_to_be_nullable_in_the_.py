"""fix the course_id to be nullable in the Section

Revision ID: e7f834924d40
Revises: 029ffcaa6809
Create Date: 2024-11-26 11:12:33.992726

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e7f834924d40'
down_revision = '029ffcaa6809'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sections', schema=None) as batch_op:
        batch_op.alter_column('course_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sections', schema=None) as batch_op:
        batch_op.alter_column('course_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)

    # ### end Alembic commands ###
