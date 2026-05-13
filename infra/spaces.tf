# DigitalOcean Space for static assets (staging)
resource "digitalocean_spaces_bucket" "assets" {
  name   = "dungeon-minus-one-assets"
  region = var.region
  acl    = "public-read"
}

# DigitalOcean Space for static assets (production)
resource "digitalocean_spaces_bucket" "assets_prod" {
  name   = "dungeon-minus-one-assets-prod"
  region = var.region
  acl    = "public-read"
}

# CORS configuration for staging (requires Spaces S3 credentials)
resource "digitalocean_spaces_bucket_cors_configuration" "assets" {
  bucket = digitalocean_spaces_bucket.assets.name
  region = var.region

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [
      "https://*.dungeonminusone.com",
      "https://dungeonminus.com"
    ]
    max_age_seconds = 3600
  }
}

# CORS configuration for production
# This bucket is the canonical/unified asset host (assets.dungeonminusone.com).
# Both staging and production pods read from it; tag-prefix isolation keeps
# releases distinct, so allowed_origins lists both app domains.
resource "digitalocean_spaces_bucket_cors_configuration" "assets_prod" {
  bucket = digitalocean_spaces_bucket.assets_prod.name
  region = var.region

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [
      "https://dungeonminusone.com",
      "https://staging.dungeonminusone.com",
    ]
    max_age_seconds = 3600
  }
}

# CDN endpoint with custom domain (staging)
resource "digitalocean_cdn" "assets_staging" {
  origin           = digitalocean_spaces_bucket.assets.bucket_domain_name
  custom_domain    = var.assets_cdn_custom_domain_staging
  certificate_name = data.digitalocean_certificate.main.name
  ttl              = 3600
}

# CDN endpoint for production assets
resource "digitalocean_cdn" "assets_prod" {
  origin           = digitalocean_spaces_bucket.assets_prod.bucket_domain_name
  custom_domain    = var.assets_cdn_custom_domain_prod
  certificate_name = data.digitalocean_certificate.main.name
  ttl              = 3600
}
