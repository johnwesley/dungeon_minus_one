output "database_host" {
  description = "PostgreSQL host"
  value       = digitalocean_database_cluster.main.host
}

output "database_port" {
  description = "PostgreSQL port"
  value       = digitalocean_database_cluster.main.port
}

output "database_user" {
  description = "PostgreSQL user"
  value       = digitalocean_database_cluster.main.user
}

output "database_password" {
  description = "PostgreSQL password"
  value       = digitalocean_database_cluster.main.password
  sensitive   = true
}

output "database_connection_string" {
  description = "Full connection string for staging database"
  value       = "postgresql+asyncpg://${digitalocean_database_cluster.main.user}:${digitalocean_database_cluster.main.password}@${digitalocean_database_cluster.main.host}:${digitalocean_database_cluster.main.port}/dungeon_staging?sslmode=require"
  sensitive   = true
}

output "database_connection_string_prod" {
  description = "Full connection string for production database"
  value       = "postgresql+asyncpg://${digitalocean_database_cluster.main.user}:${digitalocean_database_cluster.main.password}@${digitalocean_database_cluster.main.host}:${digitalocean_database_cluster.main.port}/dungeon_prod?sslmode=require"
  sensitive   = true
}

# Kubernetes outputs
output "k8s_cluster_id" {
  description = "DOKS cluster ID"
  value       = digitalocean_kubernetes_cluster.main.id
}

output "k8s_cluster_endpoint" {
  description = "DOKS cluster API endpoint"
  value       = digitalocean_kubernetes_cluster.main.endpoint
}

output "k8s_kubeconfig" {
  description = "Kubeconfig for DOKS cluster"
  value       = digitalocean_kubernetes_cluster.main.kube_config[0].raw_config
  sensitive   = true
}

# Spaces outputs (staging)

output "spaces_bucket_name_staging" {
  description = "Spaces bucket name (staging)"
  value       = digitalocean_spaces_bucket.assets.name
}

output "spaces_bucket_domain_staging" {
  description = "Spaces bucket domain (staging, direct access)"
  value       = digitalocean_spaces_bucket.assets.bucket_domain_name
}

output "spaces_cdn_endpoint_staging" {
  description = "CDN endpoint for assets (staging)"
  value       = digitalocean_cdn.assets_staging.endpoint
}

output "spaces_cdn_custom_domain_staging" {
  description = "Custom CDN domain (staging)"
  value       = digitalocean_cdn.assets_staging.custom_domain
}

# Spaces outputs (production)

output "spaces_bucket_name_prod" {
  description = "Spaces bucket name (production)"
  value       = digitalocean_spaces_bucket.assets_prod.name
}

output "spaces_bucket_domain_prod" {
  description = "Spaces bucket domain (production, direct access)"
  value       = digitalocean_spaces_bucket.assets_prod.bucket_domain_name
}

output "spaces_cdn_endpoint_prod" {
  description = "CDN endpoint for assets (production)"
  value       = digitalocean_cdn.assets_prod.endpoint
}

output "spaces_cdn_custom_domain_prod" {
  description = "Custom CDN domain (production)"
  value       = digitalocean_cdn.assets_prod.custom_domain
}

# Monitoring outputs
output "grafana_access" {
  description = "Command to access Grafana"
  value       = "kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
}
