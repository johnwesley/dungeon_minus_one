variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "ssh_allowed_ip" {
  description = "IP address allowed for SSH access (set to your own IP)"
  type        = string
  default     = ""
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc3"
}

# Kubernetes (DOKS) variables

variable "k8s_version" {
  description = "Kubernetes version for DOKS cluster"
  type        = string
  default     = "1.34.1-do.2"
}

variable "k8s_node_size" {
  description = "DOKS node pool size"
  type        = string
  default     = "s-1vcpu-2gb"
}

# Spaces S3 credentials (required for CORS configuration)

variable "spaces_access_id" {
  description = "DigitalOcean Spaces access key ID"
  type        = string
  sensitive   = true
}

variable "spaces_secret_key" {
  description = "DigitalOcean Spaces secret access key"
  type        = string
  sensitive   = true
}

# CDN custom domains

variable "assets_cdn_custom_domain_staging" {
  description = "Custom CDN domain for staging assets"
  type        = string
  default     = "assets-staging.dungeonminusone.com"
}

variable "assets_cdn_custom_domain_prod" {
  description = "Custom CDN domain for production assets"
  type        = string
  default     = "assets.dungeonminusone.com"
}
