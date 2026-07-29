#!/usr/bin/env bash
# Generates a self-signed TLS certificate for the Nginx edge layer, for
# LOCAL DEVELOPMENT ONLY. Browsers and strict HTTP clients will flag it
# as untrusted (that's expected - use `curl -k` / --insecure locally).
#
# For a real deployment, do NOT use this script. Instead:
#   - Behind a cloud load balancer: terminate TLS there with an
#     ACM/managed certificate and let this Nginx layer speak plain HTTP
#     internally, OR
#   - On a VM/bare metal: obtain a certificate from Let's Encrypt via
#     certbot (webroot or DNS-01 challenge) and point ssl_certificate /
#     ssl_certificate_key at the certbot-managed files, OR
#   - In Kubernetes: use cert-manager with a ClusterIssuer, see
#     kubernetes/cert-manager/cluster-issuer.yaml
#
# Usage: ./scripts/generate-certs.sh [output-dir]
#
# Uses an -config file rather than -subj so this works unmodified under
# Git Bash on Windows too (MSYS rewrites "/CN=..." style -subj strings as
# filesystem paths and corrupts them).

set -euo pipefail

OUT_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/nginx/certs}"
DAYS_VALID=365
COMMON_NAME="localhost"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/gateway.crt" && -f "$OUT_DIR/gateway.key" ]]; then
  echo "Certificate already exists at $OUT_DIR - remove gateway.crt/gateway.key first to regenerate."
  exit 0
fi

CNF_FILE="$(mktemp)"
trap 'rm -f "$CNF_FILE"' EXIT

cat > "$CNF_FILE" <<EOF
[req]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
x509_extensions    = ext

[dn]
C  = US
ST = Local
L  = Local
O  = Kong-Nginx-Gateway-Demo
CN = ${COMMON_NAME}

[ext]
subjectAltName = DNS:localhost,DNS:nginx,IP:127.0.0.1
EOF

echo "Generating a self-signed certificate for CN=${COMMON_NAME} (valid ${DAYS_VALID} days)..."

openssl req -x509 -nodes \
  -newkey rsa:2048 \
  -days "$DAYS_VALID" \
  -keyout "$OUT_DIR/gateway.key" \
  -out "$OUT_DIR/gateway.crt" \
  -config "$CNF_FILE"

chmod 600 "$OUT_DIR/gateway.key" 2>/dev/null || true

echo "Wrote:"
echo "  $OUT_DIR/gateway.crt"
echo "  $OUT_DIR/gateway.key"
echo ""
echo "These are self-signed and gitignored - regenerate them any time with this script."
