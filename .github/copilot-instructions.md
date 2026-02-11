# OpenClaw VPS Automation - AI Coding Agent Instructions

## Project Overview

**OpenClaw VPS** is a production-ready, security-hardened Docker deployment system for the OpenClaw AI agent (Claude-powered bot) with N8N workflow automation and OpenNotebook (NotebookLM alternative). The project emphasizes **10-layer security defense**, automated operations, and VPS deployment best practices.

**Key Technologies:** Docker Compose, PostgreSQL 16, Node.js 20 Alpine, Nginx (reverse proxy), Bash automation, Terraform (IaC), Helm/GitOps

## Architecture & Service Boundaries

### Multi-Service Docker Architecture
- **3 Docker Compose Configurations:**
  - `docker-compose.minimal.yml` - Dev testing (PostgreSQL + OpenNotebook + N8N)
  - `docker-compose.dev.yml` - Full dev environment (adds OpenClaw + Adminer)
  - `docker-compose.production.yml` - Production with Nginx SSL termination
  
- **Service Communication Pattern:**
  - Frontend Network: Internet → Nginx (443/80) → Backend services
  - Backend Network (internal only): OpenClaw, N8N, OpenNotebook, PostgreSQL
  - OpenClaw connects to N8N/OpenNotebook via internal Docker network (`http://n8n:5678`, `http://opennotebook:8080`)
  - Database: Shared PostgreSQL with schema isolation (`n8n`, `openclaw`, `opennotebook`)

- **Security Model:**
  - All services run as non-root users (UID 1001)
  - `security_opt: [no-new-privileges:true]` on all containers
  - Ports bind to `127.0.0.1` only (except Nginx)
  - UFW firewall + Fail2ban at host level
  - SSL/TLS with Let's Encrypt automated renewal

### Data Persistence
- Docker volumes: `postgres_data`, `n8n_data`, `notebook_data`, `openclaw_data`
- Host mounts: `./skills:/app/skills` (OpenClaw custom skills), `./logs/` directories
- Backup system: `scripts/backup.sh` (PostgreSQL dumps + volume tarballs)

## Critical Developer Workflows

### Essential Commands (via Makefile)
```bash
# Quick dev start (use this first!)
make minimal              # Start minimal test environment
make minimal-logs         # Follow logs
curl localhost:8080/health # Verify OpenNotebook

# Full development
make dev                  # All services including OpenClaw
make dev-logs             # Monitor all services

# Production operations
make prod                 # Production with Nginx/SSL
make health              # Comprehensive health check
make backup              # Automated backup
make scan                # Security vulnerability scan
```

### Environment Setup Pattern
1. **Always copy `.env.example` first:** `cp .env.example .env`
2. **Validate before deployment:** `./scripts/validate_env.sh` (checks 20+ required vars)
3. **Key variables:**
   - `ANTHROPIC_API_KEY` / `ZHIPUAI_API_KEY` - LLM provider
   - `DATABASE_URL` format: `postgresql://user:pass@postgres:5432/dbname`
   - `NODE_ENV=production` disables debug logging

### Testing & Debugging Flow
1. **Start minimal config:** Faster iteration, fewer dependencies
2. **Check health endpoints:** All services expose `/health` (except PostgreSQL uses `pg_isready`)
3. **Log inspection:**
   - Container logs: `docker compose -f docker-compose.minimal.yml logs -f opennotebook`
   - Host logs: `logs/openclaw/*.log`, `logs/n8n/*.log`
4. **Database debugging:**
   ```bash
   docker compose -f docker-compose.minimal.yml exec postgres psql -U openclaw
   \dn  # List schemas
   \dt opennotebook.*  # List tables in schema
   ```

### Build & Deployment Gotchas
- **OpenClaw Dockerfile:** Multi-stage build clones from `https://github.com/Sh-Osakana/open-claw.git` (external dependency)
- **UID/GID conflicts:** Avoided with `getent group` checks before user creation
- **PostgreSQL init:** SQL scripts in `docker/postgres/init/` run alphabetically on first start only (volume must be deleted to re-run)
- **Nginx SSL:** Certbot stores certs in `docker/nginx/ssl/`, auto-renews via cron (see `scripts/setup_ssl.sh`)

## Project-Specific Conventions

### Script Standards (Critical for Operations)
- **All scripts use defensive bash:**
  ```bash
  set -e  # Exit on error
  # Extensive input validation before destructive operations
  # Dry-run mode: --dry-run flag standard across scripts
  ```
- **Color-coded logging:** RED/GREEN/YELLOW output via ANSI codes (see `scripts/backup.sh` for pattern)
- **Idempotency:** Scripts check existing state (UFW rules, Fail2ban, Docker configs) before modifying

### Docker Best Practices (Non-Negotiable)
- **Non-root execution:** `USER appuser` after setup, never run as root
- **Read-only rootfs where possible:** `read_only: true` with `tmpfs` mounts
- **Health checks required:** All services define `healthcheck` with retry logic
- **Resource limits:** Always set `mem_limit` and `cpus` (see `docker-compose.yml` lines 68-69)

### File Structure Patterns
- **Scripts:** `scripts/*.sh` - All operations scripts (backup, security, maintenance)
- **Docker configs:** `docker/<service>/` - Service-specific Dockerfiles and configs
- **Init scripts:** `docker/postgres/init/*.sql` - Database initialization (numbered for order)
- **Skills:** `skills/*.js` - OpenClaw custom skills (auto-loaded from volume mount)
- **Documentation:** All-caps MD files at root (ARCHITECTURE.md, SECURITY_CHECKLIST.md, etc.)

### Security Checklist Integration
- **Before production deployment:** Run `./scripts/security_scan.sh --all` (Trivy + Docker Bench Security)
- **SSH hardening checks:** See `SECURITY_CHECKLIST.md` lines 24-36 (PermitRootLogin no, PubkeyAuthentication yes)
- **Fail2ban requirement:** Automatically configured by `scripts/setup_vps_security.sh`

## Key Integration Points

### OpenClaw ↔ N8N/OpenNotebook
- **Communication:** HTTP REST APIs over internal Docker network
- **Custom Skills:** Extend OpenClaw by adding files to `skills/` (see `skills/n8n-integration.js`)
- **Workflow Triggers:** OpenClaw calls N8N webhooks; N8N can store data in shared PostgreSQL

### PostgreSQL Schema Isolation
- **3 separate schemas:** Each service has its own namespace
- **Migrations:** Located in `docker/postgres/migrations/` (future use)
- **Connection pooling:** Services connect directly (no pgBouncer in minimal config)

### Monitoring Stack (Optional)
- **Prometheus + Grafana:** Activated via `docker-compose.monitoring.yml`
- **Metrics exposure:** Services must expose `/metrics` endpoint for scraping
- **Alertmanager:** Configured in `docker/alertmanager/alertmanager.yml`

### Terraform/Helm (IaC)
- **Terraform:** VPS provisioning on cloud providers (see `terraform/main.tf`)
- **Helm charts:** K8s deployment alternative (`helm/openclaw/`)
- **GitOps:** ArgoCD manifests in `gitops/argocd/` for CD pipeline

## Common Tasks - By Example

### Adding a new OpenClaw Skill
1. Create `skills/my-skill.js` following pattern in `skills/n8n-integration.js`
2. Export skill functions (no restart needed, volume-mounted)
3. Access via OpenClaw agent commands

### Modifying Database Schema
1. Edit `docker/postgres/init/01-init.sql` (for new deployments)
2. For existing deployments: Add migration to `docker/postgres/migrations/`
3. Test in minimal config: `make minimal-clean && make minimal`

### Troubleshooting Service Connection Issues
1. Check network: `docker network inspect openclaw_openclaw-network`
2. Verify DNS resolution: `docker exec openclaw-agent ping postgres`
3. Check service health: `docker compose ps` (should show "healthy")
4. Review logs with context: `docker compose logs --tail=100 openclaw postgres`

### Security Scan After Changes
```bash
./scripts/security_scan.sh --images-only  # Fast scan
./scripts/security_scan.sh --all          # Full audit
# Reports saved to security-reports/ with timestamp
```

## Language/Framework Specifics

### Node.js Services (OpenClaw, OpenNotebook)
- **Alpine base:** Always use `node:20-alpine` for minimal attack surface
- **Package management:** `npm ci` in Dockerfile (not `npm install`)
- **Environment loading:** Via Docker environment vars, not `.env` files in containers

### Bash Scripts
- **Argument parsing:** Use getopts or manual case statements (see `scripts/maintenance.sh`)
- **Error handling:** Validate all user inputs, provide helpful error messages
- **Cron integration:** Scripts designed for `scripts/setup_cron_jobs.sh` integration

### PostgreSQL
- **Version:** 16-alpine (specific for compatibility)
- **Locale:** `-E UTF8 --locale=C` (performance optimization)
- **Backups:** Use `pg_dump` with custom format (`-Fc`) for compression

---

**AI Context Files:** This project uses persistent context files for AI agents:
- `.claude/CLAUDE.md` - **Primary AI context** (Architecture Rules, Known Mistakes, Constraints, Agent Instructions). Always check "Known Mistakes" before attempting fixes to avoid repeating past errors.
- `.github/copilot-instructions.md` - This file. Focused on workflows, commands, and conventions.

**Documentation Priority:** When unclear, reference in order:
1. `.claude/CLAUDE.md` - AI-specific context and known mistakes
2. `QUICK_REFERENCE.md` - Command cheat sheet
3. `DEVELOPMENT.md` - Dev workflows
4. `ARCHITECTURE.md` - System design
5. `OPERATIONS_GUIDE.md` - Production operations
6. `TROUBLESHOOTING.md` - Common issues

**Code Style:** Follow existing patterns in scripts (defensive bash, color logging) and Dockerfiles (multi-stage, non-root). Security and idempotency trump brevity.
