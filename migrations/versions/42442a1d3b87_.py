"""empty message

Revision ID: 42442a1d3b87
Revises: c3e82966a54f
Create Date: 2024-12-01 23:24:40.627763

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42442a1d3b87'
down_revision = 'c3e82966a54f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('form_distributions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subject_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('professor_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(None, 'professors', ['professor_id'], ['id'])
        batch_op.create_foreign_key(None, 'subjects', ['subject_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('form_distributions', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('professor_id')
        batch_op.drop_column('subject_id')

    # ### end Alembic commands ###
