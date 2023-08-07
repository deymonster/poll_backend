"""remove unique in title poll and in type questions

Revision ID: 90bef4fde864
Revises: c753652d26b6
Create Date: 2023-05-25 12:01:20.659311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90bef4fde864'
down_revision = 'c753652d26b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_poll_title', table_name='poll')
    op.create_index(op.f('ix_poll_title'), 'poll', ['title'], unique=False)
    op.drop_index('ix_question_type', table_name='question')
    op.create_index(op.f('ix_question_type'), 'question', ['type'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_question_type'), table_name='question')
    op.create_index('ix_question_type', 'question', ['type'], unique=False)
    op.drop_index(op.f('ix_poll_title'), table_name='poll')
    op.create_index('ix_poll_title', 'poll', ['title'], unique=False)
    # ### end Alembic commands ###
