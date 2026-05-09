# DOKS (DigitalOcean Kubernetes) Cluster

resource "digitalocean_kubernetes_cluster" "main" {
  name    = "dungeon-k8s"
  region  = var.region
  version = var.k8s_version

  node_pool {
    name       = "default"
    size       = var.k8s_node_size
    auto_scale = true
    min_nodes  = 1
    max_nodes  = 4
    tags       = ["env:k8s"]
  }

  lifecycle {
    prevent_destroy = true
  }
}
