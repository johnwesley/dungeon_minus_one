# Shared PostgreSQL Cluster
resource "digitalocean_database_cluster" "main" {
  name       = "dungeon-db"
  engine     = "pg"
  version    = "18"
  size       = "db-s-1vcpu-1gb"
  region     = var.region
  node_count = 1
}

# Staging Database
resource "digitalocean_database_db" "staging" {
  cluster_id = digitalocean_database_cluster.main.id
  name       = "dungeon_staging"
}

# Production Database
resource "digitalocean_database_db" "prod" {
  cluster_id = digitalocean_database_cluster.main.id
  name       = "dungeon_prod"
}

# Allow k8s cluster to connect to the database
resource "digitalocean_database_firewall" "main" {
  cluster_id = digitalocean_database_cluster.main.id

  rule {
    type  = "k8s"
    value = digitalocean_kubernetes_cluster.main.id
  }
}
