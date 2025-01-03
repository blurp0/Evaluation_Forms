"""empty message

Revision ID: 9a64179db9b8
Revises: 55452be142a7
Create Date: 2024-12-05 10:37:13.682288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a64179db9b8'
down_revision = '55452be142a7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('professor_performance',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('professor_id', sa.Integer(), nullable=False),
    sa.Column('category_name', sa.String(length=100), nullable=False),
    sa.Column('average_grade', sa.Float(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['professor_id'], ['professors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('professor_performance')
    # ### end Alembic commands ###
