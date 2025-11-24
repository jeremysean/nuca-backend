"""Complete schema with all tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # User Consents
    op.create_table(
        'user_consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('consent_type', sa.String(100), nullable=False),
        sa.Column('granted', sa.Boolean(), default=False),
        sa.Column('granted_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('ip_address_hash', sa.String(64)),
        sa.Column('user_agent_hash', sa.String(64)),
        sa.Column('consent_version', sa.String(50), default='1.0')
    )
    op.create_index('idx_user_consent_type', 'user_consents', ['user_id', 'consent_type'])

    # Profiles
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('date_of_birth_encrypted', sa.Text()),
        sa.Column('sex', sa.String(50)),
        sa.Column('height_cm_encrypted', sa.Text()),
        sa.Column('weight_kg_encrypted', sa.Text()),
        sa.Column('activity_level', sa.String(50), default='sedentary'),
        sa.Column('has_hypertension_encrypted', sa.Text()),
        sa.Column('has_diabetes_encrypted', sa.Text()),
        sa.Column('has_heart_disease_encrypted', sa.Text()),
        sa.Column('has_kidney_disease_encrypted', sa.Text()),
        sa.Column('is_pregnant_encrypted', sa.Text()),
        sa.Column('goal_primary', sa.String(100)),
        sa.Column('daily_eer_kcal', sa.DECIMAL(10, 2)),
        sa.Column('daily_sugar_soft_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_sugar_hard_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_sodium_soft_mg', sa.DECIMAL(10, 2)),
        sa.Column('daily_sodium_hard_mg', sa.DECIMAL(10, 2)),
        sa.Column('daily_satfat_soft_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_satfat_hard_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_transfat_hard_g', sa.DECIMAL(10, 2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True))
    )

    # Family Members
    op.create_table(
        'family_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('relationship', sa.String(50), nullable=False),
        sa.Column('date_of_birth_encrypted', sa.Text()),
        sa.Column('sex', sa.String(50)),
        sa.Column('height_cm_encrypted', sa.Text()),
        sa.Column('weight_kg_encrypted', sa.Text()),
        sa.Column('activity_level', sa.String(50), default='sedentary'),
        sa.Column('health_flags_encrypted', sa.Text()),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('daily_eer_kcal', sa.DECIMAL(10, 2)),
        sa.Column('daily_sugar_soft_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_sugar_hard_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_sodium_soft_mg', sa.DECIMAL(10, 2)),
        sa.Column('daily_sodium_hard_mg', sa.DECIMAL(10, 2)),
        sa.Column('daily_satfat_soft_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_satfat_hard_g', sa.DECIMAL(10, 2)),
        sa.Column('daily_transfat_hard_g', sa.DECIMAL(10, 2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True))
    )

    # Profile Allergens
    op.create_table(
        'profile_allergens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE')),
        sa.Column('allergen_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('allergens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', sa.String(50), default='moderate')
    )

    # Family Member Allergens
    op.create_table(
        'family_member_allergens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('family_member_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_members.id', ondelete='CASCADE')),
        sa.Column('allergen_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('allergens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', sa.String(50), default='moderate')
    )

    # Products
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('barcode', sa.String(255), unique=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('brand', sa.String(255)),
        sa.Column('image_url', sa.String(500)),
        sa.Column('serving_size_label', sa.String(100)),
        sa.Column('nova_group', sa.Integer()),
        sa.Column('source', sa.String(50), default='internal'),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True))
    )
    op.create_index('idx_products_barcode', 'products', ['barcode'])

    # Product Nutritions
    op.create_table(
        'product_nutritions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('per_100g_energy_kcal', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_fat_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_saturated_fat_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_carbs_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_sugars_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_protein_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_fiber_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_salt_g', sa.DECIMAL(10, 2)),
        sa.Column('per_100g_sodium_mg', sa.DECIMAL(10, 2)),
        sa.Column('per_serving_energy_kcal', sa.DECIMAL(10, 2)),
        sa.Column('per_serving_sugars_g', sa.DECIMAL(10, 2)),
        sa.Column('per_serving_sodium_mg', sa.DECIMAL(10, 2)),
        sa.Column('per_serving_saturated_fat_g', sa.DECIMAL(10, 2))
    )

    # Product Ingredients
    op.create_table(
        'product_ingredients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name_raw', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255)),
        sa.Column('is_additive', sa.Boolean(), default=False),
        sa.Column('additive_code', sa.String(50))
    )

    # Product Allergen Tags
    op.create_table(
        'product_allergen_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('allergen_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('allergens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contain_type', sa.String(50), nullable=False)
    )

    # Ingredient Knowledgebase
    op.create_table(
        'ingredient_knowledgebase',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('normalized_name', sa.String(255), unique=True, nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('short_description', sa.Text()),
        sa.Column('risk_note', sa.Text()),
        sa.Column('child_caution', sa.Boolean(), default=False)
    )
    op.create_index('idx_ingredient_name', 'ingredient_knowledgebase', ['normalized_name'])

    # Scan Sessions
    op.create_table(
        'scan_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL')),
        sa.Column('family_member_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_members.id', ondelete='SET NULL')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scanned_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('grade', sa.String(10)),
        sa.Column('dangerous_nutrients_count', sa.Integer(), default=0),
        sa.Column('allergen_count', sa.Integer(), default=0),
        sa.Column('sugar_pct_of_limit', sa.DECIMAL(10, 2)),
        sa.Column('salt_pct_of_limit', sa.DECIMAL(10, 2)),
        sa.Column('satfat_pct_of_limit', sa.DECIMAL(10, 2)),
        sa.Column('additive_count', sa.Integer(), default=0),
        sa.Column('logged_as_consumed', sa.Boolean(), default=False)
    )
    op.create_index('idx_scan_user_date', 'scan_sessions', ['user_id', 'scanned_at'])

    # Consumption Logs
    op.create_table(
        'consumption_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('scan_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scan_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL')),
        sa.Column('family_member_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_members.id', ondelete='SET NULL')),
        sa.Column('serving_multiplier', sa.DECIMAL(5, 2), default=1.0),
        sa.Column('consumed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_consumption_date', 'consumption_logs', ['consumed_at'])

    # Product Suggestions
    op.create_table(
        'product_suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('barcode', sa.String(255)),
        sa.Column('front_image_url', sa.String(500)),
        sa.Column('nutrition_label_image_url', sa.String(500)),
        sa.Column('ingredients_image_url', sa.String(500)),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('processed_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'))
    )

    # User Subscriptions
    op.create_table(
        'user_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50)),
        sa.Column('plan', sa.String(50), default='free'),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('raw_receipt', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True))
    )

    # Product Affiliate Links
    op.create_table(
        'product_affiliate_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('partner', sa.String(100), nullable=False),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100)),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('ip_address_hash', sa.String(64)),
        sa.Column('user_agent_hash', sa.String(64)),
        sa.Column('metadata_json', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action', 'created_at'])

    # Data Deletion Requests
    op.create_table(
        'data_deletion_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('scheduled_deletion_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(50), default='pending')
    )


def downgrade():
    op.drop_table('data_deletion_requests')
    op.drop_table('audit_logs')
    op.drop_table('product_affiliate_links')
    op.drop_table('user_subscriptions')
    op.drop_table('product_suggestions')
    op.drop_table('consumption_logs')
    op.drop_table('scan_sessions')
    op.drop_table('ingredient_knowledgebase')
    op.drop_table('product_allergen_tags')
    op.drop_table('product_ingredients')
    op.drop_table('product_nutritions')
    op.drop_table('products')
    op.drop_table('family_member_allergens')
    op.drop_table('profile_allergens')
    op.drop_table('family_members')
    op.drop_table('profiles')
    op.drop_table('user_consents')