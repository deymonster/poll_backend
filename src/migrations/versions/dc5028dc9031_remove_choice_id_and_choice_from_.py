"""Remove choice_id and choice from Response

Revision ID: dc5028dc9031
Revises: ca0561879905
Create Date: 2024-02-14 10:48:40.069597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc5028dc9031'
down_revision = 'ca0561879905'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('response_choice_id_fkey', 'response', type_='foreignkey')
    op.drop_column('response', 'choice_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('response', sa.Column('choice_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('response_choice_id_fkey', 'response', 'choice', ['choice_id'], ['id'])
    # ### end Alembic commands ###
