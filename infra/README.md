# Infrastructure

OpenTofu configuration for DigitalOcean Kubernetes (DOKS) environment.

See [root README](../README.md) for deployment instructions.

## Files

| File | Description |
|------|-------------|
| `main.tf` | Provider config, SSH key, certificate data sources |
| `variables.tf` | Input variables (region, k8s version, node size) |
| `database.tf` | PostgreSQL cluster, database, firewall |
| `k8s-cluster.tf` | DOKS cluster with auto-scaling node pool |
| `outputs.tf` | Output values (cluster endpoint, kubeconfig) |
| `.env.deploy.example` | Template for deployment credentials |
