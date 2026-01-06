# Oracle Cloud Free Tier Deployment Guide

Complete step-by-step guide to deploy Software Builder on Oracle Cloud's **always-free** tier.

---

## Prerequisites

- Email address for Oracle Cloud account
- Credit/debit card for verification (never charged for free tier)
- Git installed on your local machine
- Your Google Gemini API key

---

## Part 1: Create Oracle Cloud Account

### Step 1: Sign Up

1. Go to [cloud.oracle.com/free](https://cloud.oracle.com/free)
2. Click **"Start for free"**
3. Fill in your details:
   - Country/Territory
   - Email address
   - Name
4. Verify your email

### Step 2: Complete Profile

1. Set your cloud account name (e.g., `softwarebuilder`)
2. Choose your **Home Region** (pick one close to you, you can't change this later!)
   - Recommended: `US East (Ashburn)`, `UK South (London)`, or your nearest region
3. Enter payment method (for verification only)
4. Complete verification

### Step 3: Confirm Free Resources

Once logged in, verify you have access to:
- **2 AMD Compute VMs** (1/8 OCPU, 1GB RAM each)
- **4 ARM Ampere A1 Compute VMs** (24GB RAM total, 4 OCPUs total) ← **We'll use this!**
- **200GB Block Storage**
- **10GB Object Storage**

---

## Part 2: Create ARM Virtual Machine

### Step 1: Navigate to Compute

1. Log into Oracle Cloud Console
2. Click the hamburger menu (☰) → **Compute** → **Instances**
3. Click **"Create instance"**

### Step 2: Configure Instance

**Name**: `software-builder-vm`

**Placement**: Leave default

**Image and shape**:
1. Click **"Edit"**
2. Change Image: Select **"Ubuntu"** → **"Canonical Ubuntu 22.04"**
3. Change Shape: 
   - Click **"Change shape"**
   - Select **"Ampere"** (ARM processors)
   - Shape: **VM.Standard.A1.Flex**
   - OCPUs: **4** (max for free tier)
   - Memory: **24 GB** (max for free tier)

**Networking**:
1. Create new VCN or use existing
2. Create new subnet or use existing
3. **IMPORTANT**: Assign public IPv4 address = **Yes**

**Add SSH keys**:
1. Select **"Generate a key pair for me"**
2. Click **"Save private key"** and **"Save public key"**
3. Store these SAFELY - you need them to connect!

### Step 3: Create Instance

Click **"Create"** and wait 2-3 minutes for the instance to provision.

### Step 4: Note Your Public IP

Once running, note the **Public IP address** (e.g., `129.159.xx.xx`)

---

## Part 3: Configure Firewall Rules

### Step 1: Open VCN Security List

1. Click on your instance name
2. Under **Primary VNIC** → Click the **Subnet** link
3. Click the **Security List** (default security list)

### Step 2: Add Ingress Rules

Click **"Add Ingress Rules"** and add these:

| Source CIDR | Protocol | Destination Port | Description |
|-------------|----------|------------------|-------------|
| `0.0.0.0/0` | TCP | 80 | HTTP |
| `0.0.0.0/0` | TCP | 443 | HTTPS |
| `0.0.0.0/0` | TCP | 5000 | Backend API |
| `0.0.0.0/0` | TCP | 3000 | Frontend |

---

## Part 4: Setup the Server

### Step 1: Connect via SSH

```bash
# On Windows (PowerShell)
ssh -i path\to\your-private-key.key ubuntu@YOUR_PUBLIC_IP

# On Mac/Linux
chmod 400 ~/path/to/your-private-key.key
ssh -i ~/path/to/your-private-key.key ubuntu@YOUR_PUBLIC_IP
```

### Step 2: Run Setup Script

Once connected:

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/Software-builder.git /opt/software-builder

# Navigate to deploy folder
cd /opt/software-builder/deploy

# Run setup script
chmod +x oracle-setup.sh
./oracle-setup.sh

# IMPORTANT: Log out and back in for Docker permissions
exit
```

### Step 3: Reconnect and Continue

```bash
ssh -i your-key.key ubuntu@YOUR_PUBLIC_IP
cd /opt/software-builder
```

---

## Part 5: Configure and Deploy

### Step 1: Create Environment File

```bash
# Copy template
cp deploy/.env.production.template .env

# Edit with your values
nano .env
```

Update these values:
```env
GOOGLE_API_KEY=your_actual_gemini_api_key
POSTGRES_PASSWORD=choose_a_strong_password_here
```

### Step 2: Build Frontend

```bash
cd coordinator/ui
npm install
npm run build
cd ../..
```

### Step 3: Start Services

```bash
docker-compose -f deploy/docker-compose.prod.yml up -d
```

### Step 4: Check Services

```bash
# Check all containers are running
docker ps

# Check logs if needed
docker-compose -f deploy/docker-compose.prod.yml logs -f
```

---

## Part 6: Configure Nginx (Optional but Recommended)

### Step 1: Install Nginx Config

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/software-builder

# Edit the config
sudo nano /etc/nginx/sites-available/software-builder
# Replace YOUR_DOMAIN_OR_IP with your public IP or domain

# Enable the site
sudo ln -s /etc/nginx/sites-available/software-builder /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 2: (Optional) Setup SSL with Let's Encrypt

If you have a domain name:

```bash
sudo certbot --nginx -d your-domain.com
```

---

## Part 7: Access Your Application

### Without Nginx:
- Frontend: `http://YOUR_PUBLIC_IP:3000`
- Backend API: `http://YOUR_PUBLIC_IP:5000`
- Health Check: `http://YOUR_PUBLIC_IP:5000/health`

### With Nginx:
- Full App: `http://YOUR_PUBLIC_IP` (or `https://your-domain.com`)

---

## Verification Checklist

- [ ] Can access frontend at port 3000 (or 80 with nginx)
- [ ] `/health` returns `{"status": "healthy"}`
- [ ] `/api/builds` returns `{"builds": []}`
- [ ] Can create a new build from the UI
- [ ] Sandbox preview works (Docker containers spawn)

---

## Troubleshooting

### Can't connect to SSH?
- Check security list ingress rules include port 22
- Verify you're using the correct private key
- Use `ubuntu` as the username (not `root`)

### Containers won't start?
```bash
# Check logs
docker-compose -f deploy/docker-compose.prod.yml logs

# Check disk space
df -h

# Restart
docker-compose -f deploy/docker-compose.prod.yml down
docker-compose -f deploy/docker-compose.prod.yml up -d
```

### Sandbox containers fail?
```bash
# Verify Docker socket is mounted
docker ps
docker run hello-world

# Check coordinator has socket access
docker logs sb-coordinator
```

---

## Maintenance Commands

```bash
# Update application
cd /opt/software-builder
git pull
docker-compose -f deploy/docker-compose.prod.yml up -d --build

# View logs
docker-compose -f deploy/docker-compose.prod.yml logs -f coordinator

# Stop everything
docker-compose -f deploy/docker-compose.prod.yml down

# Backup database
docker exec sb-postgres pg_dump -U softwarebuilder appbuilder > backup.sql
```

---

## Cost: $0 Forever! 💰

Oracle's Always Free tier includes:
- 4 ARM OCPUs + 24GB RAM
- 200GB block storage
- 10TB/month outbound data

**As long as you stay within these limits, you will never be charged.**
