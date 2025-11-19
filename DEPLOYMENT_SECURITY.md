# NUCA Backend - Deployment & Security Guide

## Data Protection Compliance (GDPR/CCPA)

### Encryption at Rest
All sensitive health data is encrypted using AES-256 before storage:
- Date of birth
- Height & weight measurements
- Health conditions (hypertension, diabetes, heart disease, kidney disease, pregnancy)
- Family member health data

**Implementation:** `app/security/encryption.py`

### Encryption in Transit
- All API communication over HTTPS/TLS
- Supabase connections use SSL
- Security headers enforced (HSTS, CSP, X-Frame-Options)

### User Consent Management
Required consents before processing:
1. **Health Data Processing** - Required for personalized limits
2. **Personalized Grading** - Required for product recommendations
3. **Family Data Processing** - Required for family member profiles
4. **Analytics** - Optional
5. **Marketing** - Optional

**API Endpoints:**
- `POST /api/v1/consent/` - Grant or revoke consent
- `GET /api/v1/consent/` - List all user consents
- `GET /api/v1/consent/{type}` - Check specific consent status

### Audit Logging
All sensitive operations logged in `audit_logs` table:
- Profile creation/update/deletion
- Consent changes
- Data exports
- Data deletion requests

**Retention:** Audit logs retained for 7 years for compliance.

### User Rights (GDPR/CCPA)

#### Right to Access
Users can export all their data via API:
```
GET /api/v1/user/export
```
Returns JSON with all profiles, scans, consumption logs.

#### Right to Rectification
Users can update profiles anytime:
```
PUT /api/v1/profiles/{id}
PUT /api/v1/family-members/{id}
```

#### Right to Erasure (Right to be Forgotten)
```
POST /api/v1/user/delete-request
```
- Grace period: 30 days
- Full deletion includes:
  - All profiles & family members (cascades)
  - Scan sessions & consumption logs
  - Consents & audit logs
  - Supabase Auth account

#### Right to Data Portability
Export returns machine-readable JSON format compatible with other systems.

#### Right to Withdraw Consent
```
POST /api/v1/consent/
Body: { "consent_type": "...", "granted": false }
```
Immediate effect - features requiring consent become unavailable.

---

## Environment Configuration

### Required Environment Variables

```bash
# Supabase (from dashboard)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=your-jwt-secret

# Database (from Supabase settings -> Database)
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres

# OpenFoodFacts API
OPENFOODFACTS_API_URL=https://world.openfoodfacts.org/api/v2

# Security
ENCRYPTION_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">

# CORS
CORS_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]

# Compliance
GDPR_ENABLED=true
CCPA_ENABLED=true
DATA_RETENTION_DAYS=730

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## Deployment Steps

### 1. Supabase Setup

#### Create Project
1. Go to https://supabase.com
2. Create new project
3. Select region: **Singapore (ap-southeast-1)** for Indonesia
4. Save credentials

#### Run Migrations
```bash
# Install Supabase CLI
npm install -g supabase

# Link project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

#### Configure Auth
1. Go to Authentication -> Providers
2. Enable:
   - Google (for Android/iOS)
   - Apple (for iOS)
   - Email (optional)
3. Add redirect URLs:
   - `nuca://callback` (for mobile deep linking)

#### Create Storage Buckets
```sql
-- Create product images bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('product-images', 'product-images', true);

-- Create product suggestions bucket (private)
INSERT INTO storage.buckets (id, name, public)
VALUES ('product-suggestions', 'product-suggestions', false);

-- Set policies
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'product-images');

CREATE POLICY "Authenticated users can upload suggestions"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'product-suggestions' AND auth.uid() IS NOT NULL);
```

### 2. Backend Deployment (Render/Railway)

#### Using Render

1. Connect GitHub repo
2. Create Web Service
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3.11
4. Add environment variables from `.env.example`
5. Deploy

#### Using Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Add environment variables
railway variables set SUPABASE_URL=...
railway variables set DATABASE_URL=...

# Deploy
railway up
```

### 3. Database Initialization

```bash
# Run from backend directory
python -m alembic upgrade head

# Seed allergens
python -c "
from app.database import SessionLocal
from app.models import Allergen
import uuid

db = SessionLocal()
allergens = [
    ('GLUTEN', 'Gluten', 'Found in wheat, barley, rye'),
    ('MILK', 'Milk/Dairy', 'Lactose and milk proteins'),
    ('EGG', 'Eggs', 'Egg proteins'),
    ('PEANUT', 'Peanuts', 'Peanut allergens'),
    ('TREE_NUT', 'Tree Nuts', 'Almonds, cashews, walnuts'),
    ('FISH', 'Fish', 'Fish proteins'),
    ('SHELLFISH', 'Shellfish', 'Shrimp, crab, lobster'),
    ('SOY', 'Soy', 'Soy proteins'),
    ('SESAME', 'Sesame', 'Sesame seeds'),
]

for code, name, desc in allergens:
    allergen = Allergen(id=uuid.uuid4(), code=code, name=name, description=desc)
    db.add(allergen)

db.commit()
"
```

### 4. Monitoring Setup

#### UptimeRobot
1. Sign up at https://uptimerobot.com
2. Add monitor:
   - Type: HTTP(s)
   - URL: `https://your-api.render.com/healthz`
   - Interval: 5 minutes
3. Add alerts:
   - Email
   - Slack webhook (optional)

---

## Security Checklist

### Pre-Launch
- [ ] All environment variables set
- [ ] Encryption key generated securely
- [ ] CORS origins configured correctly
- [ ] HTTPS enabled (automatic on Render/Railway)
- [ ] Rate limiting configured
- [ ] Supabase region matches target market
- [ ] JWT secret is strong (256-bit)
- [ ] Database backups enabled (Supabase automatic)

### Post-Launch
- [ ] Monitor `/healthz` endpoint
- [ ] Check error logs daily
- [ ] Review audit logs weekly
- [ ] Test data export/deletion flows
- [ ] Verify consent withdrawal works
- [ ] Check encryption/decryption performance
- [ ] Monitor API response times

---

## Compliance Documentation

### Privacy Policy Location
Available at: `GET /api/v1/privacy-policy`

**Contents:**
- Data collected (with explicit list)
- Data usage purposes
- Data protection measures
- User rights under GDPR/CCPA
- Data retention policy
- Contact information

### Terms of Service Location
Available at: `GET /api/v1/terms-of-service`

**Key Disclaimers:**
- Not a medical device
- Not medical advice
- Informational purposes only
- User responsibility to verify product data
- Consultation with healthcare professionals required

### Consent Version Control
All consents stored with version number (currently "1.0").
If privacy policy changes materially, increment version and re-request consent.

---

## Data Minimization Practices

NUCA only collects data necessary for core functionality:

**Collected:**
- Health conditions (for personalized limits)
- Height/weight (for EER calculation)
- Age (for age-appropriate recommendations)
- Allergens (for safety warnings)

**NOT Collected:**
- Full medical history
- Real-time location
- Social connections
- Financial data
- Browsing history outside app

---

## Incident Response Plan

### Data Breach Protocol
1. **Detect:** Monitor audit logs, error rates
2. **Contain:** Rotate encryption keys if compromised
3. **Assess:** Determine scope (which users affected)
4. **Notify:** Email affected users within 72 hours (GDPR requirement)
5. **Report:** Notify supervisory authority if required
6. **Remediate:** Patch vulnerability, update security measures

### Contact
Data Protection Officer: privacy@nuca.care

---

## Testing

### Health Data Encryption Test
```bash
# From backend directory
python -c "
from app.security.encryption import encryption_service

# Test encryption
original = 'true'
encrypted = encryption_service.encrypt_boolean(True)
decrypted = encryption_service.decrypt_boolean(encrypted)
print(f'Original: {original}')
print(f'Encrypted: {encrypted}')
print(f'Decrypted: {decrypted}')
assert str(decrypted) == original, 'Encryption failed!'
print('✅ Encryption test passed')
"
```

### Consent Flow Test
```bash
# Test consent requirement
curl -X POST https://your-api.com/api/v1/profiles/ \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "date_of_birth": "1990-01-01", "sex": "male"}'

# Expected: 403 Forbidden if consent not granted
```

---

## Performance Optimization

### Database Indexes
Already defined in models:
- `users.supabase_user_id` (unique index)
- `scan_sessions(user_id, scanned_at)` (composite index)
- `audit_logs(user_id, action, created_at)` (composite index)

### Caching Strategy
- Product data: Cache frequently scanned products (Redis future phase)
- Personal limits: Computed once per profile update, stored in DB
- OpenFoodFacts responses: Cache for 24 hours

### Query Optimization
- Use `.first()` instead of `.all()` when single result expected
- Eager load relationships with `joinedload()` for N+1 prevention
- Limit large list queries with pagination

---

## Backup & Recovery

### Automated Backups (Supabase)
- Daily automatic backups
- 7-day retention on free tier
- Point-in-time recovery on paid tier

### Manual Backup
```bash
# Export schema
pg_dump -s $DATABASE_URL > schema_backup.sql

# Export data (excluding logs)
pg_dump -t users -t profiles -t products $DATABASE_URL > data_backup.sql
```

### Disaster Recovery
1. Create new Supabase project
2. Restore schema: `psql $NEW_DATABASE_URL < schema_backup.sql`
3. Restore data: `psql $NEW_DATABASE_URL < data_backup.sql`
4. Update environment variables
5. Redeploy backend

Recovery Time Objective (RTO): < 4 hours
Recovery Point Objective (RPO): < 24 hours

---

## Maintenance

### Weekly Tasks
- Review error logs
- Check disk usage
- Monitor API latency
- Review new product suggestions

### Monthly Tasks
- Security patch updates
- Dependency updates (`pip list --outdated`)
- Review audit logs for anomalies
- Data retention cleanup (automated)

### Quarterly Tasks
- Privacy policy review
- Penetration testing
- Compliance audit
- Backup restoration test

---

## Support & Contact

**Technical Issues:**
support@nuca.care

**Privacy/Data Requests:**
privacy@nuca.care

**Security Vulnerabilities:**
security@nuca.care

**Response Time:** < 48 hours for privacy requests (GDPR requirement)
