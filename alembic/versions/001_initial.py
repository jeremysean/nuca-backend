"""Initial schema with encrypted health data

Revision ID: 001
Revises: 
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Optional tapi bagus: pastikan fungsi gen_random_uuid() ada
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 1) Buat tabel users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supabase_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('email_encrypted', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('data_retention_acknowledged', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supabase_user_id')
    )

    op.create_index(
        op.f('ix_users_supabase_user_id'),
        'users',
        ['supabase_user_id'],
        unique=True
    )

    # 2) Buat tabel allergens
    op.create_table(
        'allergens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    )

    # 3) Seed data ke allergens
    op.execute("""
        INSERT INTO allergens (id, code, name, description) VALUES
        (gen_random_uuid(), 'GLUTEN', 'Gluten', 'Found in wheat, barley, rye'),
        (gen_random_uuid(), 'MILK', 'Milk/Dairy', 'Lactose and milk proteins'),
        (gen_random_uuid(), 'EGG', 'Eggs', 'Egg proteins'),
        (gen_random_uuid(), 'PEANUT', 'Peanuts', 'Peanut allergens'),
        (gen_random_uuid(), 'TREE_NUT', 'Tree Nuts', 'Almonds, cashews, walnuts, etc'),
        (gen_random_uuid(), 'FISH', 'Fish', 'Fish proteins'),
        (gen_random_uuid(), 'SHELLFISH', 'Shellfish', 'Shrimp, crab, lobster'),
        (gen_random_uuid(), 'SOY', 'Soy', 'Soy proteins'),
        (gen_random_uuid(), 'SESAME', 'Sesame', 'Sesame seeds');
    """)


def downgrade():
    # urutan kebalik dari upgrade
    op.drop_table('allergens')
    op.drop_index(op.f('ix_users_supabase_user_id'), table_name='users')
    op.drop_table('users')
