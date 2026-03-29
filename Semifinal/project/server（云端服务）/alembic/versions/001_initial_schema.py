"""Initial schema."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('phone', sa.String(20), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('cpr_certified', sa.Boolean, default=False),
        sa.Column('fcm_token', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'incidents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('phase', sa.String(30), nullable=False, default='CREATED'),
        sa.Column('lat', sa.Float, nullable=True),
        sa.Column('lng', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_incidents_phase', 'incidents', ['phase'])
    op.create_index('ix_incidents_created_at', 'incidents', ['created_at'])

    op.create_table(
        'incident_roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('incident_id', sa.String(36), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, default='JOINED'),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'incident_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('incident_id', sa.String(36), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('msg', sa.Text, nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'aed_locations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('lat', sa.Float, nullable=False),
        sa.Column('lng', sa.Float, nullable=False),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('floor', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
    )


def downgrade() -> None:
    op.drop_table('aed_locations')
    op.drop_table('incident_logs')
    op.drop_table('incident_roles')
    op.drop_index('ix_incidents_created_at', 'incidents')
    op.drop_index('ix_incidents_phase', 'incidents')
    op.drop_table('incidents')
    op.drop_table('users')
