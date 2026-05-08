# Prometheus + Grafana monitoring stack

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
  }

  depends_on = [digitalocean_kubernetes_cluster.main]
}

resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "75.9.0"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name

  # Large chart needs more time to install
  timeout         = 600  # 10 minutes
  wait            = true
  wait_for_jobs   = false
  atomic          = false
  cleanup_on_fail = false
  replace         = true  # Replace if exists from failed install

  # Ensure CRDs are created
  set {
    name  = "crds.enabled"
    value = "true"
  }

  # Disable AlertManager (not currently used)
  set {
    name  = "alertmanager.enabled"
    value = "false"
  }

  # Reduce resource usage for small cluster
  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "7d"
  }

  set {
    name  = "prometheus.prometheusSpec.resources.requests.memory"
    value = "256Mi"
  }

  set {
    name  = "prometheus.prometheusSpec.resources.requests.cpu"
    value = "100m"
  }

  set {
    name  = "grafana.resources.requests.memory"
    value = "128Mi"
  }

  set {
    name  = "grafana.resources.requests.cpu"
    value = "50m"
  }

  # Enable pod annotation scraping (for our app)
  set {
    name  = "prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues"
    value = "false"
  }

  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }

  # Enable Grafana sidecar to discover dashboards in the monitoring namespace
  set {
    name  = "grafana.sidecar.dashboards.searchNamespace"
    value = "monitoring"
  }

  # PostgreSQL datasource for staging player metrics
  set {
    name  = "grafana.additionalDataSources[0].name"
    value = "PostgreSQL-staging"
  }

  set {
    name  = "grafana.additionalDataSources[0].uid"
    value = "PostgreSQL-staging"
  }

  set {
    name  = "grafana.additionalDataSources[0].type"
    value = "postgres"
  }

  set {
    name  = "grafana.additionalDataSources[0].url"
    value = "${digitalocean_database_cluster.main.host}:${digitalocean_database_cluster.main.port}"
  }

  set {
    name  = "grafana.additionalDataSources[0].database"
    value = "dungeon_staging"
  }

  set_sensitive {
    name  = "grafana.additionalDataSources[0].user"
    value = digitalocean_database_cluster.main.user
  }

  set_sensitive {
    name  = "grafana.additionalDataSources[0].secureJsonData.password"
    value = digitalocean_database_cluster.main.password
  }

  set {
    name  = "grafana.additionalDataSources[0].jsonData.sslmode"
    value = "require"
  }

  # PostgreSQL datasource for production player metrics
  set {
    name  = "grafana.additionalDataSources[1].name"
    value = "PostgreSQL-prod"
  }

  set {
    name  = "grafana.additionalDataSources[1].uid"
    value = "PostgreSQL-prod"
  }

  set {
    name  = "grafana.additionalDataSources[1].type"
    value = "postgres"
  }

  set {
    name  = "grafana.additionalDataSources[1].url"
    value = "${digitalocean_database_cluster.main.host}:${digitalocean_database_cluster.main.port}"
  }

  set {
    name  = "grafana.additionalDataSources[1].database"
    value = "dungeon_prod"
  }

  set_sensitive {
    name  = "grafana.additionalDataSources[1].user"
    value = digitalocean_database_cluster.main.user
  }

  set_sensitive {
    name  = "grafana.additionalDataSources[1].secureJsonData.password"
    value = digitalocean_database_cluster.main.password
  }

  set {
    name  = "grafana.additionalDataSources[1].jsonData.sslmode"
    value = "require"
  }

  depends_on = [kubernetes_namespace.monitoring]
}
