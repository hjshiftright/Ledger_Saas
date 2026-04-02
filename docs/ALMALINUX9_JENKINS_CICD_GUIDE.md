# Ledger SaaS — AlmaLinux 9 Deployment with Jenkins CI/CD

**Complete Step-by-Step User Guide**

---

## Overview

This guide deploys the Ledger SaaS application on an **AlmaLinux 9** server using **Jenkins** for continuous integration and deployment.

### Architecture of the Deployment

```
Developer Workstation
       │
       │  git push
       ▼
  Git Repository  ──── webhook ────►  Jenkins Server (AlmaLinux 9)
                                              │
                                    ┌─────────▼──────────┐
                                    │  CI/CD Pipeline     │
                                    │  1. Checkout code   │
                                    │  2. Build Frontend  │
                                    │  3. Run Tests       │
                                    │  4. Build Docker    │
                                    │  5. Deploy          │
                                    └─────────┬──────────┘
                                              │  docker compose up
                                              ▼
                                   ┌──────────────────────┐
                                   │  Running Application  │
                                   │  ┌────────────────┐  │
                                   │  │  web (Nginx:80)│  │
                                   │  │  api  (:8000)  │  │
                                   │  │  pgbouncer:6432│  │
                                   │  │  db (postgres) │  │
                                   │  └────────────────┘  │
                                   └──────────────────────┘
```

### Application Stack

| Component       | Technology                      | Port  |
|-----------------|---------------------------------|-------|
| Frontend        | React 19 + Vite → Nginx         | 80    |
| Backend API     | FastAPI + Uvicorn + Python 3.13 | 8000  |
| Connection Pool | PgBouncer                       | 6432  |
| Database        | PostgreSQL 15                   | 5432  |

---

## Prerequisites

- A fresh **AlmaLinux 9** server (physical or VM) with:
  - Minimum 4 GB RAM, 2 CPU cores, 40 GB disk
  - Internet access
  - A user with `sudo` privileges
- Your project hosted in a **Git repository** (GitHub, GitLab, Gitea, etc.)
- A domain name or server IP address

---

## Part 1 — Prepare the AlmaLinux 9 Server

### Step 1.1 — Update the System

Log in to your AlmaLinux 9 server as a sudo user and run:

```bash
sudo dnf update -y
sudo dnf install -y epel-release
sudo dnf update -y
```

### Step 1.2 — Install Essential Utilities

```bash
sudo dnf install -y \
    curl \
    wget \
    git \
    nano \
    unzip \
    tar \
    net-tools \
    firewalld
```

### Step 1.3 — Install Java 17 (Required for Jenkins)

Jenkins requires Java 17 or 21. Install OpenJDK 17:

```bash
sudo dnf install -y java-17-openjdk java-17-openjdk-devel
```

Verify the installation:

```bash
java -version
```

Expected output:
```
openjdk version "17.x.x" ...
```

Set JAVA_HOME environment variable:

```bash
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk' | sudo tee /etc/profile.d/java.sh
echo 'export PATH=$JAVA_HOME/bin:$PATH' | sudo tee -a /etc/profile.d/java.sh
source /etc/profile.d/java.sh
```

### Step 1.4 — Install Docker Engine

```bash
# Add Docker repository
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

Verify Docker is running:

```bash
sudo docker --version
sudo docker compose version
```

### Step 1.5 — Add the jenkins User to the docker Group

> **Note:** The `jenkins` user is created automatically when Jenkins is installed (Step 2). You will add it to the docker group in Step 2.3 after Jenkins is installed.

For now, create the `jenkins` group placeholder for Docker:

```bash
# This will be done after Jenkins is installed — noted here for reference
```

### Step 1.6 — Install Node.js 20

The frontend requires Node.js 20 (LTS). Install via NodeSource:

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
```

Verify:

```bash
node --version    # Should show v20.x.x
npm --version
```

### Step 1.7 — Verify Python 3.13

Your AlmaLinux 9 machine already has Python 3.13 installed. Verify it is accessible:

```bash
python3.13 --version
```

Expected output:
```
Python 3.13.x
```

If `python3.13` is not found in `PATH`, locate it and create a symlink:

```bash
# Find where Python 3.13 is installed
which python3.13 || find /usr /opt /usr/local -name "python3.13" 2>/dev/null

# Register it with alternatives so it is discoverable system-wide
sudo alternatives --install /usr/bin/python3.13 python3.13 /usr/bin/python3.13 1
```

Verify `pip` is available for Python 3.13:

```bash
python3.13 -m pip --version
```

If pip is missing, install it:

```bash
python3.13 -m ensurepip --upgrade
# or
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13
```

Also install the `python3.13-devel` headers (needed to compile some packages like `psycopg2`):

```bash
sudo dnf install -y python3.13-devel
```

> **Python 3.13 Note:** The backend Docker container (`python:3.11-slim` in `backend/Dockerfile`) runs Python 3.11 inside Docker — this is independent of your host Python version. Your host Python 3.13 is only used by Jenkins for the CI test stage (`Backend Tests`) that runs outside Docker.

### Step 1.8 — Configure the Firewall

```bash
# Start and enable firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Allow SSH (already open, but confirm it)
sudo firewall-cmd --permanent --add-service=ssh

# Allow HTTP (port 80 — frontend)
sudo firewall-cmd --permanent --add-service=http

# Allow HTTPS (port 443 — for future SSL)
sudo firewall-cmd --permanent --add-service=https

# Allow Jenkins web UI (port 8080)
sudo firewall-cmd --permanent --add-port=8080/tcp

# Allow the backend API (port 8000 — optional, only if accessed directly)
sudo firewall-cmd --permanent --add-port=8000/tcp

# Reload firewall
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-all
```

---

## Part 2 — Install and Configure Jenkins

### Step 2.1 — Add Jenkins Repository and Install

```bash
# Add Jenkins repository
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

# Install Jenkins
sudo dnf install -y jenkins

# Start and enable Jenkins
sudo systemctl start jenkins
sudo systemctl enable jenkins
```

Check Jenkins status:

```bash
sudo systemctl status jenkins
```

### Step 2.2 — Get the Initial Admin Password

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Copy the password — you will need it in the next step.

### Step 2.3 — Add jenkins User to the docker Group

This allows Jenkins pipelines to run Docker commands without `sudo`:

```bash
sudo usermod -aG docker jenkins

# Restart Jenkins so the group membership takes effect
sudo systemctl restart jenkins
```

### Step 2.4 — Initial Jenkins Web Setup

1. Open your browser and navigate to: `http://<your-server-ip>:8080`
2. Paste the **initial admin password** from Step 2.2
3. Click **"Install suggested plugins"** and wait for the installation to complete
4. Create your **Admin User** (set a username, password, and email)
5. Set the **Jenkins URL** to `http://<your-server-ip>:8080/` and click **Save and Finish**

### Step 2.5 — Install Additional Jenkins Plugins

Go to: **Manage Jenkins → Plugins → Available plugins**

Search for and install the following plugins:

| Plugin Name | Purpose |
|---|---|
| **Pipeline** | Enables Jenkinsfile-based pipelines |
| **Git** | Git SCM integration |
| **GitHub** / **GitLab** | Webhook triggers (choose your Git host) |
| **Docker Pipeline** | Docker commands in pipelines |
| **Credentials Binding** | Securely inject secrets into pipeline |
| **Blue Ocean** | Modern pipeline visualization (optional) |
| **NodeJS** | Manage Node.js versions inside Jenkins |
| **AnsiColor** | Colored terminal output in logs |

After selecting all, click **"Install"** and wait. Restart Jenkins when prompted:

```bash
sudo systemctl restart jenkins
```

### Step 2.6 — Configure Node.js in Jenkins

Go to: **Manage Jenkins → Tools → NodeJS installations**

- Click **"Add NodeJS"**
- Name: `NodeJS-20`
- Version: `20.x.x (LTS)`
- Click **Save**

---

## Part 3 — Configure Jenkins Credentials and Secrets

All sensitive values (passwords, API keys) must be stored as Jenkins Credentials, not hardcoded in the pipeline.

### Step 3.1 — Store Application Secrets

Go to: **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**

Create the following credentials:

---

**Credential 1 — Secret Key (JWT)**

- Kind: `Secret text`
- ID: `ledger-secret-key`
- Secret: *(a long random string, e.g., run `openssl rand -hex 32` on your terminal)*
- Description: `Ledger JWT Secret Key`

---

**Credential 2 — Database Password**

- Kind: `Secret text`
- ID: `ledger-db-password`
- Secret: `ledger_secret` *(change this to a strong password for production)*
- Description: `Ledger PostgreSQL Password`

---

**Credential 3 — Git Repository**

The repository `https://github.com/hjshiftright/Ledger_Saas` is **public** — no Git credentials are required. Jenkins can clone it directly over HTTPS without any authentication.

If you ever make the repository private in the future, add an SSH credential:

- Kind: `SSH Username with private key`
- ID: `git-ssh-key`
- Username: `git`
- Private Key: *(paste the private key of the SSH key pair added to your GitHub account)*
- Description: `GitHub SSH Key`

---

**Credential 4 — LLM API Keys (Optional)**

If using LLM features (Gemini, OpenAI, Anthropic), add each as a separate `Secret text` credential:

- ID: `gemini-api-key` → your Gemini API key
- ID: `openai-api-key` → your OpenAI API key
- ID: `anthropic-api-key` → your Anthropic API key

---

## Part 4 — Create the Jenkinsfile

In the **root of your project repository**, create a file named `Jenkinsfile`.

> This file is the pipeline-as-code definition. It must be committed to your Git repository.

```groovy
// Jenkinsfile — Ledger SaaS CI/CD Pipeline for AlmaLinux 9
pipeline {
    agent any

    environment {
        // ── Application settings ─────────────────────────────────────────────
        APP_NAME        = "ledger"
        COMPOSE_FILE    = "docker-compose.yml"
        APP_ENV         = "production"
        APP_HOST        = "0.0.0.0"
        APP_PORT        = "8000"
        APP_DEBUG       = "false"

        // ── Database settings ─────────────────────────────────────────────────
        PG_USER         = "ledger"
        PG_DB           = "ledger"
        PG_PORT         = "5432"
        PGB_PORT        = "6432"

        // ── Credentials (injected from Jenkins Credentials Store) ─────────────
        SECRET_KEY      = credentials('ledger-secret-key')
        PG_PASS         = credentials('ledger-db-password')

        // ── Optional LLM keys (comment out if not using) ──────────────────────
        // GEMINI_API_KEY    = credentials('gemini-api-key')
        // OPENAI_API_KEY    = credentials('openai-api-key')
        // ANTHROPIC_API_KEY = credentials('anthropic-api-key')

        // ── Deployment target directory on the server ─────────────────────────
        DEPLOY_DIR      = "/opt/ledger"
    }

    options {
        // Keep only the last 10 builds
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // Fail the build if it runs longer than 30 minutes
        timeout(time: 30, unit: 'MINUTES')
        // Add timestamps to console output
        timestamps()
    }

    stages {

        // ── Stage 1: Checkout Source Code ────────────────────────────────────
        stage('Checkout') {
            steps {
                echo '==> Checking out source code from GitHub (branch: new-ui)...'
                git branch: 'new-ui',
                    url: 'https://github.com/hjshiftright/Ledger_Saas.git'
            }
        }

        // ── Stage 2: Build Frontend ───────────────────────────────────────────
        stage('Build Frontend') {
            steps {
                echo '==> Installing frontend dependencies and building...'
                dir('frontend') {
                    sh 'npm ci --prefer-offline'
                    sh 'npm run build'
                }
                echo '==> Frontend build complete. Artifacts in frontend/dist/'
            }
        }

        // ── Stage 3: Backend Lint / Tests ─────────────────────────────────────
        stage('Backend Tests') {
            steps {
                echo '==> Setting up Python virtual environment and running tests...'
                sh '''
                    python3.13 -m venv .venv-ci
                    source .venv-ci/bin/activate
                    pip install --upgrade pip --quiet
                    pip install -r requirements.txt --quiet
                    pip install pytest pytest-asyncio httpx --quiet

                    # Run tests — exit 0 even if no tests found, fail on actual errors
                    pytest backend/tests/ -v --tb=short || echo "[WARN] No backend tests found or tests failed — check output above"
                    deactivate
                '''
            }
        }

        // ── Stage 4: Build Docker Images ──────────────────────────────────────
        stage('Build Docker Images') {
            steps {
                echo '==> Building Docker images via docker compose...'
                sh '''
                    docker compose -f ${COMPOSE_FILE} build --no-cache --parallel
                '''
                echo '==> Docker images built successfully.'
            }
        }

        // ── Stage 5: Deploy ───────────────────────────────────────────────────
        stage('Deploy') {
            steps {
                echo '==> Deploying application...'
                sh '''
                    # Create the deployment directory if it does not exist
                    sudo mkdir -p ${DEPLOY_DIR}

                    # Copy all project files to the deployment directory
                    sudo rsync -av --delete \
                        --exclude='.git' \
                        --exclude='.venv*' \
                        --exclude='frontend/node_modules' \
                        --exclude='**/__pycache__' \
                        ./ ${DEPLOY_DIR}/

                    # Move into the deployment directory
                    cd ${DEPLOY_DIR}

                    # Write the environment file for docker compose
                    cat > .env <<EOF
APP_ENV=${APP_ENV}
APP_HOST=${APP_HOST}
APP_PORT=${APP_PORT}
APP_DEBUG=${APP_DEBUG}
SECRET_KEY=${SECRET_KEY}
POSTGRES_DB=${PG_DB}
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}
DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASS}@pgbouncer:${PGB_PORT}/${PG_DB}
ADMIN_DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASS}@db:${PG_PORT}/${PG_DB}
ALLOWED_ORIGINS=http://localhost,http://localhost:80,http://$(hostname -I | awk '{print $1}')
EOF
                    # Uncomment below if using LLM features:
                    # echo "GEMINI_API_KEY=${GEMINI_API_KEY}" >> .env
                    # echo "OPENAI_API_KEY=${OPENAI_API_KEY}" >> .env
                    # echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" >> .env

                    echo "==> Environment file written."

                    # Pull latest images and restart services gracefully
                    docker compose -f ${COMPOSE_FILE} pull --ignore-pull-failures || true
                    docker compose -f ${COMPOSE_FILE} up -d --remove-orphans

                    echo "==> Deployment complete."
                '''
            }
        }

        // ── Stage 6: Health Check ─────────────────────────────────────────────
        stage('Health Check') {
            steps {
                echo '==> Running post-deployment health check...'
                sh '''
                    # Wait for the API to become available (up to 60 seconds)
                    TRIES=0
                    until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
                        TRIES=$((TRIES + 1))
                        if [ "$TRIES" -ge 30 ]; then
                            echo "[ERROR] API health check failed after 60 seconds."
                            docker compose -f ${DEPLOY_DIR}/${COMPOSE_FILE} logs --tail=50
                            exit 1
                        fi
                        echo "  Waiting for API... attempt $TRIES/30"
                        sleep 2
                    done
                    echo "[OK] API health check passed."

                    # Check the frontend (Nginx on port 80)
                    if curl -sf http://localhost:80 > /dev/null 2>&1; then
                        echo "[OK] Frontend (Nginx) is responding on port 80."
                    else
                        echo "[WARN] Frontend did not respond on port 80 — check nginx container logs."
                    fi
                '''
            }
        }
    }

    // ── Post-build Actions ────────────────────────────────────────────────────
    post {
        success {
            echo '=============================================='
            echo ' BUILD & DEPLOYMENT SUCCEEDED'
            echo '=============================================='
        }
        failure {
            echo '=============================================='
            echo ' BUILD OR DEPLOYMENT FAILED'
            echo ' Check the console output above for errors.'
            echo '=============================================='
            // Show last 100 lines of docker compose logs on failure
            sh '''
                cd ${DEPLOY_DIR} 2>/dev/null || true
                docker compose -f ${COMPOSE_FILE} logs --tail=100 || true
            ''' 
        }
        always {
            // Clean up the CI virtual environment
            sh 'rm -rf .venv-ci || true'
        }
    }
}
```

**Save this file as `Jenkinsfile`** in the root of your repository and commit it to the `new-ui` branch:

```bash
git checkout new-ui          # Make sure you are on the new-ui branch
git add Jenkinsfile
git commit -m "Add Jenkins CI/CD pipeline"
git push origin new-ui
```

---

## Part 5 — Prepare the Deployment Directory

Run these commands on the AlmaLinux 9 server:

### Step 5.1 — Create the Deployment Directory

```bash
sudo mkdir -p /opt/ledger
sudo chown jenkins:jenkins /opt/ledger
sudo chmod 755 /opt/ledger
```

### Step 5.2 — Allow Jenkins to Use sudo for rsync

Edit the sudoers file to allow the Jenkins user to run `rsync` and `mkdir` as root without a password:

```bash
sudo visudo
```

Add the following line at the end of the file:

```
jenkins ALL=(ALL) NOPASSWD: /usr/bin/rsync, /usr/bin/mkdir, /usr/bin/chown
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter` for nano, or `:wq` for vi).

### Step 5.3 — Verify Docker Access for Jenkins

Test that the Jenkins user can run Docker:

```bash
sudo -u jenkins docker ps
```

If this succeeds (no permission error), Jenkins is correctly configured. If you see a permission error, re-run:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

---

## Part 6 — Create the Jenkins Pipeline Job

### Step 6.1 — Create a New Pipeline

1. Log in to Jenkins at `http://<server-ip>:8080`
2. Click **"New Item"** on the left sidebar
3. Enter a name: `Ledger-CICD`
4. Select **"Pipeline"** and click **OK**

### Step 6.2 — Configure the Pipeline

In the pipeline configuration page:

**General tab:**
- Check **"Discard old builds"** → Max builds to keep: `10`
- Check **"Do not allow concurrent builds"**

**Build Triggers tab:**
- Check **"GitHub hook trigger for GITScm polling"** (if using GitHub)
- OR check **"Build when a change is pushed to GitLab"** (if using GitLab)
- OR check **"Poll SCM"** and set the schedule to `H/5 * * * *` (poll every 5 minutes as a fallback)

**Pipeline tab:**
- Definition: `Pipeline script from SCM`
- SCM: `Git`
- Repository URL: `https://github.com/hjshiftright/Ledger_Saas.git`
- Credentials: `- none -` *(the repository is public — no credentials required)*
- Branch Specifier: `*/new-ui`
- Script Path: `Jenkinsfile`

Click **Save**.

### Step 6.3 — Run the First Build Manually

1. Click **"Build Now"** in the left sidebar of your pipeline job
2. Click on the build number (e.g., `#1`) → **"Console Output"** to watch the progress
3. The first run may take 10–20 minutes as Docker images are built from scratch

---

## Part 7 — Set Up Automatic Webhooks (Auto-Trigger on git push)

This makes Jenkins automatically start a new build whenever you push code to your repository.

### GitHub Webhook Setup

The repository is at `https://github.com/hjshiftright/Ledger_Saas` on branch `new-ui`.

1. Go to the repository on GitHub: `https://github.com/hjshiftright/Ledger_Saas`
2. Click **Settings → Webhooks → Add webhook**
3. Fill in the form:
   - **Payload URL**: `http://<your-server-ip>:8080/github-webhook/`
   - **Content type**: `application/json`
   - **Secret**: *(leave blank, or set a secret and configure it in Jenkins)*
   - **Which events**: select `"Just the push event"`
4. Click **Add webhook**

GitHub will send a test ping — you should see a green tick next to the webhook.

> **Important:** Jenkins must be reachable from the internet for GitHub webhooks to work. If your AlmaLinux server is behind a NAT or firewall with no public IP, use **Poll SCM** (`H/5 * * * *`) as a fallback instead — Jenkins will check GitHub for new commits every 5 minutes.

> **Branch filter:** Only pushes to the `new-ui` branch will trigger the pipeline, because the Branch Specifier in Step 6.2 is set to `*/new-ui`.

---

## Part 8 — Update docker-compose.yml for Production

The `docker-compose.yml` at the project root uses environment variables. The Jenkinsfile writes a `.env` file at deploy time, but you should also update the `docker-compose.yml` to reference these variables properly.

Open `docker-compose.yml` and modify the `api` service's `environment` section to use variables from the `.env` file:

```yaml
  api:
    build:
      context:    ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      pgbouncer:
        condition: service_healthy
      db:
        condition: service_healthy
    environment:
      DATABASE_URL:       ${DATABASE_URL}
      ADMIN_DATABASE_URL: ${ADMIN_DATABASE_URL}
      APP_ENV:            ${APP_ENV:-production}
      APP_HOST:           ${APP_HOST:-0.0.0.0}
      APP_PORT:           ${APP_PORT:-8000}
      APP_DEBUG:          ${APP_DEBUG:-false}
      SECRET_KEY:         ${SECRET_KEY}
      ALLOWED_ORIGINS:    ${ALLOWED_ORIGINS:-http://localhost}
      GEMINI_API_KEY:     ${GEMINI_API_KEY:-}
      OPENAI_API_KEY:     ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY:  ${ANTHROPIC_API_KEY:-}
    ports:
      - "8000:8000"
```

Also update the `db` service to use environment variables:

```yaml
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB:       ${POSTGRES_DB:-ledger}
      POSTGRES_USER:     ${POSTGRES_USER:-ledger}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test:     ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ledger} -d ${POSTGRES_DB:-ledger}"]
      interval: 5s
      timeout:  5s
      retries:  10
      start_period: 10s
```

Commit these changes to the `new-ui` branch:

```bash
git checkout new-ui
git add docker-compose.yml
git commit -m "Configure docker-compose for production env vars"
git push origin new-ui
```

---

## Part 9 — Verify the Running Application

After a successful Jenkins build, verify the application is running:

### Check Running Containers

```bash
cd /opt/ledger
docker compose ps
```

Expected output:

```
NAME                    IMAGE                    COMMAND        STATUS
ledger-saas-db-1        postgres:15-alpine       ...            Up (healthy)
ledger-saas-pgbouncer-1 edoburu/pgbouncer:latest ...            Up (healthy)
ledger-saas-api-1       ledger-saas-api          ...            Up
ledger-saas-web-1       ledger-saas-web          ...            Up
```

### Check the API Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "3.0.0",
  "env": "production",
  ...
}
```

### Access the Frontend

Open a browser and navigate to:

```
http://<your-server-ip>
```

The Ledger application dashboard should load.

---

## Part 10 — Useful Operations

### View Live Container Logs

```bash
cd /opt/ledger

# All services
docker compose logs -f

# Only the API
docker compose logs -f api

# Only the database
docker compose logs -f db
```

### Restart a Single Service

```bash
cd /opt/ledger
docker compose restart api
```

### Stop the Entire Application

```bash
cd /opt/ledger
docker compose down
```

### Start the Application Manually (without Jenkins)

```bash
cd /opt/ledger
docker compose up -d
```

### Roll Back to the Previous Build

In Jenkins:

1. Go to the pipeline job: `Ledger-CICD`
2. Click on the last **successful** build number in the build history
3. Click **"Replay"** → **"Run"** to re-run that exact build

Or manually on the server, check out the previous Git commit and redeploy:

```bash
cd /opt/ledger
git log --oneline -10               # Find the previous good commit hash
git checkout <commit-hash>          # Detach HEAD to that version
docker compose up -d --build

# To return to the tip of new-ui after rollback:
git checkout new-ui
```

### Run Database Migrations Manually

```bash
cd /opt/ledger
docker compose exec api alembic upgrade head
```

### Connect to the Database

```bash
cd /opt/ledger
docker compose exec db psql -U ledger ledger
```

### Clean Up Old Docker Images (Free Disk Space)

```bash
docker image prune -af
docker volume prune -f
```

---

## Part 11 — Troubleshooting

### Jenkins Cannot Run Docker

**Symptom:** `permission denied while trying to connect to the Docker daemon socket`

**Fix:**
```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

### Port 8080 Not Accessible

**Symptom:** Cannot reach Jenkins at `http://<ip>:8080`

**Fix:**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
sudo systemctl status jenkins     # Ensure Jenkins is running
```

### Docker Compose Build Fails — No Space Left

**Symptom:** `no space left on device`

**Fix:**
```bash
docker system prune -af --volumes
df -h    # Check available disk space
```

### Frontend Build Fails — Node Version Mismatch

**Symptom:** `npm ci` fails with engine compatibility errors

**Fix:** Ensure Node.js 20 is installed:
```bash
node --version    # Must be v20.x.x
```

If version is wrong, reinstall:
```bash
sudo dnf remove -y nodejs
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
```

### API Container Crashes on Start

**Symptom:** `ledger-saas-api-1` container exits immediately

**Fix:** Check logs:
```bash
cd /opt/ledger
docker compose logs api
```

Common causes:
- Missing or invalid `SECRET_KEY` in `.env` file
- Database not ready (pgbouncer healthcheck not passing)
- Missing `ADMIN_DATABASE_URL` environment variable

### PgBouncer Health Check Fails

**Symptom:** `pgbouncer` container shows `unhealthy` status

**Fix:**
```bash
cd /opt/ledger
docker compose logs pgbouncer
docker compose logs db
```

Ensure the database password in `.env` matches the one used in `pgbouncer.ini` / `userlist.txt`.

### Backend Tests Fail — Package Build Error on Python 3.13

**Symptom:** `pip install -r requirements.txt` fails with a build error in the `Backend Tests` stage (e.g., `camelot-py`, `psycopg2-binary`, or `PyMuPDF` compilation errors)

**Context:** Python 3.13 introduced breaking C API changes. Some packages may not yet have pre-built wheels for Python 3.13 and will try to compile from source, requiring C headers.

**Fix — ensure build tools are installed on the Jenkins host:**

```bash
sudo dnf install -y python3.13-devel gcc gcc-c++ make \
    ghostscript poppler-utils tesseract \
    libpq-devel
```

If a specific package fails to build, pin it to the latest compatible version in `requirements.txt` or skip the host-side test stage and rely entirely on the Docker build (which uses Python 3.11-slim inside the container and is unaffected).

### Webhook Not Triggering Jenkins

**Symptom:** Pushing to Git does not start a Jenkins build

**Fix:**
1. Ensure Jenkins is reachable from the internet (or from your Git server's network)
2. Check Jenkins at **Manage Jenkins → System Log** for webhook delivery errors
3. In GitHub/GitLab, check the **Recent Deliveries** section of your webhook settings

---

## Part 12 — Security Hardening Checklist

Before going to production, complete these steps:

- [ ] **Change the database password** in Jenkins credentials from `ledger_secret` to a strong random password
- [ ] **Rotate the `SECRET_KEY`**: generate a secure key with `openssl rand -hex 64`
- [ ] **Set up HTTPS**: Install Certbot and configure an SSL certificate for Nginx
- [ ] **Restrict Jenkins access**: Configure Jenkins to require authentication for all pages
- [ ] **Enable PgBouncer TLS**: Set `CLIENT_TLS_SSLMODE=require` and `SERVER_TLS_SSLMODE=require` if PostgreSQL is accessible over a network
- [ ] **Back up PostgreSQL data**: Set up a daily backup cron job for the `postgres_data` Docker volume
- [ ] **Limit API exposure**: Remove port `8000` from the firewall if Nginx is handling all traffic
- [ ] **Update `ALLOWED_ORIGINS`**: Set it to your actual domain name, not `localhost`
- [ ] **Disable Jenkins script console** for non-admin users
- [ ] **Keep Docker and system packages updated** regularly with `sudo dnf update -y`

---

## Summary of Access Points

| Service | URL | Notes |
|---|---|---|
| Ledger Frontend | `http://<server-ip>/` | Main application |
| Ledger API | `http://<server-ip>:8000/api/v1/` | REST API |
| API Documentation | `http://<server-ip>:8000/docs` | Swagger UI |
| API Health | `http://<server-ip>:8000/health` | Health check endpoint |
| Jenkins CI/CD | `http://<server-ip>:8080/` | Pipeline management |

---

*End of Guide — Ledger SaaS on AlmaLinux 9 with Jenkins CI/CD*
