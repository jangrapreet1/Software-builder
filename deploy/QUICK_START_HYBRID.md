# Quick Start: Hybrid Deployment (2 AMD Instances)

## Step-by-Step Checklist

### ☐ Step 1: Create Instance 1 (App Server)

1. Oracle Cloud Console → Compute → Instances → Create
2. Name: `sb-app-server`
3. Shape: **VM.Standard.E2.1.Micro** (Specialty and previous generation)
4. Image: **Canonical Ubuntu 22.04 Minimal**
5. VCN: Your existing `sb-vcn`, Public subnet
6. ✅ Assign public IPv4 address
7. Generate SSH keys → Save as `app-server-key.key`
8. Create instance
9. **Note Public IP**: `___.___.___.___`

---

### ☐ Step 2: Create Instance 2 (Database Server)

1. Create another instance
2. Name: `sb-db-server`
3. Same shape, image, networking as above
4. Generate SSH keys → Save as `db-server-key.key`
5. Create instance
6. **Note Public IP**: `___.___.___.___`

---

### ☐ Step 3: Setup Database Server

```bash
# Connect
ssh -i db-server-key.key ubuntu@DB_SERVER_IP

# Install PostgreSQL
sudo apt update && sudo apt install -y postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE appbuilder;
CREATE USER softwarebuilder WITH PASSWORD 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE appbuilder TO softwarebuilder;
\q

# Allow remote connections
sudo nano /etc/postgresql/14/main/postgresql.conf
# Change: listen_addresses = '*'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: host appbuilder softwarebuilder 10.0.0.0/24 md5

sudo systemctl restart postgresql

# Get private IP
hostname -I
# Note the 10.0.0.x address
```

---

### ☐ Step 4: Setup Application Server

```bash
# Connect
ssh -i app-server-key.key ubuntu@APP_SERVER_IP

# Clone repo (push your changes to GitHub first!)
git clone https://github.com/YOUR_USERNAME/Software-builder.git /opt/software-builder

# Run setup
cd /opt/software-builder/deploy
chmod +x oracle-setup-hybrid.sh
./oracle-setup-hybrid.sh

# Log out and back in
exit
ssh -i app-server-key.key ubuntu@APP_SERVER_IP
```

---

### ☐ Step 5: Configure Environment

```bash
cd /opt/software-builder
cp deploy/.env.production.template .env
nano .env
```

Update:
```env
GOOGLE_API_KEY=your_actual_gemini_key
POSTGRES_PASSWORD=YOUR_PASSWORD
DATABASE_URL=postgresql://softwarebuilder:YOUR_PASSWORD@DB_PRIVATE_IP:5432/appbuilder
```

---

### ☐ Step 6: Build and Deploy

```bash
# Build frontend
cd coordinator/ui
npm install
npm run build
cd ../..

# Start services
docker-compose -f deploy/docker-compose.hybrid.yml up -d

# Check status
docker ps
```

---

### ☐ Step 7: Configure Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/software-builder
sudo nano /etc/nginx/sites-available/software-builder
# Replace YOUR_DOMAIN_OR_IP with your app server IP

sudo ln -s /etc/nginx/sites-available/software-builder /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

### ☐ Step 8: Test

Visit: `http://APP_SERVER_IP`

Check health: `http://APP_SERVER_IP/health`

---

## Before You Start

**Push your code to GitHub:**
```bash
git add deploy/
git commit -m "Add hybrid deployment configuration"
git push
```

---

## Troubleshooting

**Can't connect to database?**
```bash
# From app server
psql -h DB_PRIVATE_IP -U softwarebuilder -d appbuilder
```

**Out of memory?**
```bash
free -h  # Check memory
docker stats  # Check container usage
```

**Services won't start?**
```bash
docker-compose -f deploy/docker-compose.hybrid.yml logs
```
