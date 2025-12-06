# Deployment Guide: Digital Ocean Droplet (VM) with Docker Compose

This guide details how to deploy the Dungeon Minus One application to a Digital Ocean Droplet (Ubuntu VM) using Docker Compose and a PostgreSQL database. This approach ensures persistent storage and a production-ready environment.

## Prerequisites

-   A [Digital Ocean](https://www.digitalocean.com/) account.
-   A GitHub repository containing this code.
-   `doctl` CLI installed locally (optional, for creating the Droplet).

## Configuration Files

-   `Dockerfile`: Defines the Python environment.
-   `docker-compose.prod.yml`: Defines the services (App + PostgreSQL).
-   `scripts/setup_vm.sh`: Helper script to install Docker on the VM.

## Steps to Deploy

### 1. Create a Droplet

Create a Basic Droplet (e.g., Ubuntu 24.04, Basic CPU, 1GB RAM - $6/mo).
Add your SSH key.

### 2. SSH into the Droplet

```bash
ssh root@<your_droplet_ip>
```

### 3. Install Docker

Copy the setup script or run these commands:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### 4. Clone the Repository

```bash
git clone https://github.com/johnwesley/dungeon_minus_one.git /opt/dungeon-minus-one
cd /opt/dungeon-minus-one
```

### 5. Configure Environment Variables

Create a `.env` file in `/opt/dungeon-minus-one`:

```bash
nano .env
```

Paste the following content (replace placeholders):

```ini
# App
ANTHROPIC_API_KEY=sk-ant-...
AUTH_SECRET_KEY=change_this_to_a_secure_random_string

# Database
POSTGRES_USER=dungeon_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=dungeon_db
```

### 6. Start the Application

Run the production compose file:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 7. Verify Deployment

-   The app should be running at `http://<your_droplet_ip>:8080`.
-   The database is now persistent in a Docker volume (`postgres_data`).
-   The `start.sh` script runs automatically to seed the database with locations.

### 8. Configure Load Balancer (Optional)

If using a Digital Ocean Load Balancer for TLS termination:

1.  **Forwarding Rules**:
    -   **Entry Protocol**: HTTPS (Port 443)
    -   **Target Protocol**: HTTP (Port 8080)
    -   **Certificate**: Select or create your SSL certificate.
2.  **Health Checks**:
    -   **Protocol**: HTTP
    -   **Port**: 8080
    -   **Path**: `/health` (or `/` if no health endpoint exists)
3.  **Droplet**: Add your droplet to the Load Balancer.

The Load Balancer will handle HTTPS on port 443 and forward traffic to your Droplet on port 8080.

## Updating the App

To deploy changes:

1.  Pull the latest code:
    ```bash
    git pull origin main
    ```
2.  Rebuild and restart containers:
    ```bash
    docker compose -f docker-compose.prod.yml up -d --build
    ```

