# Dungeon Minus One

A conversational text-adventure game powered by Claude.

## Production Configuration

Docker Compose is used for production deployment.

**Environment Variables** (create `.env` file):
```ini
ANTHROPIC_API_KEY=sk-ant-...
AUTH_SECRET_KEY=<secure_random_string>
POSTGRES_USER=dungeon_user
POSTGRES_PASSWORD=<your_db_password>
POSTGRES_DB=dungeon_db
```

**Start production**:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

- App runs on port 8080
- Uses PostgreSQL (not SQLite)
- Database persisted via Docker volume (`postgres_data`)

## User Management & Invites

The game uses an invite-only system. Administrators must generate invite codes for new players to register.

### 1. Creating the First Admin User

Since the database starts empty, you must manually create the first admin user via the command line on your server.

1.  SSH into your Droplet:
    ```bash
    ssh root@<your_droplet_ip>
    ```
2.  Run the create admin script inside the app container:
    ```bash
    cd /opt/dungeon-minus-one
    docker compose -f docker-compose.prod.yml exec app python scripts/create_admin.py <USERNAME> <PASSWORD>
    ```
    *Example:*
    ```bash
    docker compose -f docker-compose.prod.yml exec app python scripts/create_admin.py admin mysecurepassword
    ```

### 2. Generating Invite Codes

To let friends play, you need to generate invite codes for them.

1.  Run the generation script:
    ```bash
    docker compose -f docker-compose.prod.yml exec app python scripts/generate_invite.py
    ```
2.  The output will look like:
    ```
    Invite Code Generated: a1b2c3d4
    ```
3.  Send this code to your friend.

### 3. How Friends Join

1.  Give your friend the **Invite Code** and the **URL** to your game:
    `http://<your_droplet_ip>:8000/static/register.html`
2.  They enter the code, choose a username/password, and are automatically logged in.

### 4. Logging In

Once registered, users can log in at:
`http://<your_droplet_ip>:8000/static/login.html`
