# Kong + Nginx API Gateway Reference Platform

A reference implementation of a layered API gateway: **Nginx terminates
TLS at the edge**, **Kong Gateway (DB-less/declarative) does the actual
API gateway work** - routing, key-auth, rate-limiting, CORS, and request
logging - in front of three minimal backend services. Ships with a
working Docker Compose stack for local development and a parallel
Kubernetes path (Kong Ingress Controller via Helm, Ingress resources,
cert-manager notes) as the production target.

This is a demo/reference architecture built for a portfolio, not a
production deployment. Everything in it runs and is real config, but the
backend services are intentionally trivial and the numbers below describe
this repo only - not a claim about capacity in any real environment.

## Why two layers (Nginx *and* Kong)?

It would be possible to have Kong terminate TLS directly and skip Nginx
entirely - Kong can do that. This repo deliberately layers them instead,
because that's the pattern you actually see in production estates:

- **Nginx is the outer edge.** It's the one thing exposed to the
  internet/host network, it terminates TLS, and it's where you'd put
  connection-level protections (rate limits by IP at the network layer,
  request size caps, slow-loris mitigations) that you want to enforce
  *before* a request is even parsed as an API call. It's also the natural
  place to load-balance across multiple Kong replicas - the `upstream`
  block in `nginx/conf.d/gateway.conf` round-robins across every Kong
  instance listed there.
- **Kong is the API gateway layer.** Once a request is decrypted and past
  the edge, Kong owns everything that's actually about the API contract:
  which route this is, whether the caller is authenticated, whether
  they've exceeded their rate limit, what gets logged about the call. This
  is config that changes far more often than TLS/edge concerns, and Kong's
  declarative model (`kong.yml`) means those changes are a reviewable diff,
  not a click through an Admin UI.
- **Practically:** it also means Kong's Admin API and proxy port never
  need to be reachable from outside the Docker network / cluster at all -
  Nginx (or, in the Kubernetes path, the cloud load balancer in front of
  Kong's Service) is the only thing with a public-facing port.

## Architecture

```
                                   Internet / local host
                                            │
                                            ▼
                         ┌──────────────────────────────────┐
                         │   Nginx (edge)                    │
                         │   - TLS termination (443)         │
                         │   - HTTP -> HTTPS redirect (80)    │
                         │   - reverse proxy / load balancer  │
                         │     across Kong replicas           │
                         └──────────────────┬─────────────────┘
                                            │ plain HTTP, inside the
                                            │ Docker network only
                                            ▼
                         ┌──────────────────────────────────┐
                         │   Kong Gateway (DB-less)           │
                         │   declarative config: kong/kong.yml │
                         │                                     │
                         │   Routes:                          │
                         │   /api/users   -> key-auth,         │
                         │                   rate-limit (20/m) │
                         │   /api/orders  -> rate-limit (5/m)  │
                         │   /api/reports -> rate-limit (10/m),│
                         │                   short timeouts    │
                         │                                     │
                         │   Global: CORS, file-log,           │
                         │           correlation-id            │
                         └───┬────────────┬────────────┬───────┘
                             │            │            │
                             ▼            ▼            ▼
                    ┌────────────┐ ┌─────────────┐ ┌────────────────┐
                    │users-service│ │orders-service│ │reports-service │
                    │Node/Express │ │Node/Express  │ │Python/FastAPI  │
                    │:3001        │ │:3002         │ │:8000           │
                    │routes: /,   │ │routes: /,    │ │routes: /,      │
                    │  /:id       │ │  /:id        │ │  /slow (~5s),  │
                    │(Kong strips │ │(Kong strips  │ │  /:id          │
                    │ /api/users) │ │ /api/orders) │ │(strips /api/   │
                    │             │ │              │ │ reports)       │
                    └────────────┘ └─────────────┘ └────────────────┘
```

Kubernetes path (see [`kubernetes/`](kubernetes/)): the same routing and
plugin story, but Kong Ingress Controller reads standard `Ingress` +
`KongPlugin`/`KongConsumer` CRDs instead of a mounted `kong.yml`, and
cert-manager replaces `scripts/generate-certs.sh` for real TLS. Nginx
itself is not part of the Kubernetes path - a cloud load balancer (or
ingress-nginx, if you want a second edge layer there too) fills that role
instead.

## Repository structure

```
services/
  users-service/         Node/Express - GET /, /:id, /health (reached via
                          the gateway as /api/users, /api/users/:id - Kong
                          strips the /api/users prefix, see kong/kong.yml)
  orders-service/         Node/Express - GET /, /:id, /health (as /api/orders, /api/orders/:id)
  reports-service/         Python/FastAPI - GET /, /slow (~5s), /:id, /health
                          (as /api/reports, /api/reports/slow, /api/reports/:id)

kong/
  kong.yml                DB-less declarative config: services, routes,
                          consumers, and plugins (key-auth, rate-limiting,
                          cors, file-log, correlation-id)

nginx/
  nginx.conf              Base Nginx config (logging format, includes conf.d/)
  conf.d/gateway.conf     TLS termination, HTTP->HTTPS redirect, reverse
                          proxy + upstream/load-balancing block to Kong
  certs/                  Generated locally, gitignored (see below)

scripts/
  generate-certs.sh       Self-signed cert generator for local dev

docker-compose.yml        Full local stack: 3 services + Kong + Nginx
.env.example               Non-secret local config (ports, demo API key)

kubernetes/
  namespace.yaml           gateway-demo namespace
  backend-services/         Deployment + Service per sample service
  kong/helm-values.yaml     Values for the official kong/kong Helm chart
                            (Kong Gateway + Kong Ingress Controller)
  ingress/
    ingress.yaml            Ingress per service
    kong-plugins.yaml        KongPlugin / KongClusterPlugin CRDs
    kong-consumers.yaml      Demo KongConsumer + key-auth credential Secret
  cert-manager/
    cluster-issuer.yaml      Let's Encrypt ClusterIssuer examples (staging + prod)

.github/workflows/ci.yaml  Lint/validate everything above, plus a real
                            docker-compose-based end-to-end smoke test
```

## Prerequisites

- Docker Desktop (or Docker Engine + the Compose plugin) - `docker compose version` should work
- OpenSSL (for generating the local dev certificate) - present by default on macOS/Linux; on Windows, Git Bash (ships with Git for Windows) or WSL both include it
- `curl`, to exercise the routes
- For the Kubernetes path only: `kubectl`, `helm`, access to a cluster (kind/minikube work fine for trying it out)

## Run it locally

```bash
git clone <this-repo>
cd Kong-Nginx-Gateway

# 1. Non-secret local config (ports, demo API key). Defaults work as-is.
cp .env.example .env

# 2. Generate a self-signed cert for the Nginx edge layer (local dev only)
./scripts/generate-certs.sh

# 3. Build and start everything
docker compose up --build
```

Wait for all five containers to report healthy (`docker compose ps`), then
in another terminal:

```bash
# Unauthenticated route, through Nginx -> Kong -> orders-service.
# -k because the cert is self-signed - see "TLS certificates" below.
curl -k https://localhost:8443/api/orders

# Key-auth-protected route: fails without a key
curl -k https://localhost:8443/api/users
# -> 401 {"message":"No API key found in request"}

# ...succeeds with the demo key (also in .env.example / kong/kong.yml)
curl -k -H "apikey: demo-key-CHANGE-ME-6f3a9c1d" https://localhost:8443/api/users

# Rate limiting: the orders route allows 5 requests/minute. Run this
# a 6th+ time within the same minute and Kong returns 429.
for i in 1 2 3 4 5 6; do
  curl -k -s -o /dev/null -w "request $i -> %{http_code}\n" https://localhost:8443/api/orders
done

# Slow endpoint - reports-service intentionally sleeps ~5s, but Kong's
# route for reports-service has read_timeout: 3000ms, so Kong gives up on
# the upstream first and this returns 504 (not the 5s response body).
# Lower reports-service's read_timeout further in kong/kong.yml, or make
# the sleep shorter, to see the two race the other way.
curl -k -i https://localhost:8443/api/reports/slow

# Response headers worth looking at: X-Kong-Request-Id (correlation-id
# plugin), X-RateLimit-Remaining-Minute, X-Upstream-Service (set by the
# backend service itself, proving the request actually reached it).
curl -k -i https://localhost:8443/api/orders 2>&1 | grep -i -E "x-kong|x-ratelimit|x-upstream"
```

Kong's Admin API is published to `localhost:8001` for local inspection
only (`curl http://localhost:8001/status`) - it is **not** routed through
Nginx and must never be exposed outside the host/cluster network in a
real deployment.

Tear down with `docker compose down` (add `-v` to also drop the network).

### TLS certificates

`scripts/generate-certs.sh` creates a self-signed certificate under
`nginx/certs/` (gitignored - regenerate any time, nothing there is meant
to be committed). It's for local development only; every browser and most
HTTP clients will refuse it by default, hence `curl -k` above.

For real production use, do **not** use a self-signed cert. Instead:

- **Behind a cloud load balancer** (ALB/NLB, Cloud Load Balancing, etc.):
  terminate TLS there with a managed certificate and let this Nginx layer
  speak plain HTTP internally.
- **On a VM/bare metal**: obtain a certificate via `certbot` (Let's
  Encrypt) and point `ssl_certificate` / `ssl_certificate_key` in
  `nginx/conf.d/gateway.conf` at the certbot-managed files, with a renewal
  cron/systemd timer.
- **In Kubernetes**: use cert-manager - see
  `kubernetes/cert-manager/cluster-issuer.yaml` and the comments in
  `kubernetes/kong/helm-values.yaml` for how the resulting Secret plugs
  into Kong's proxy TLS listener.

## Kubernetes path

The Docker Compose stack is the primary, fully-working local
demonstration. The Kubernetes manifests under `kubernetes/` are a real,
valid alternative deployment target - reviewed and YAML/schema-validated
in CI - but they have **not** been applied against a live cluster as part
of building this repo (no cluster was available in the environment this
was built in). Treat them as a solid starting point; validate with
`helm template` / `kubectl apply --dry-run=server` against your actual
cluster and chart version before relying on them.

```bash
kubectl apply -f kubernetes/namespace.yaml

# Kong Gateway + Kong Ingress Controller (DB-less)
helm repo add kong https://charts.konghq.com
helm repo update
helm install kong kong/kong -n gateway-demo -f kubernetes/kong/helm-values.yaml

# Sample backend services - build/push images first, see the comment
# at the top of each file in kubernetes/backend-services/
kubectl apply -f kubernetes/backend-services/

# Plugins, consumer/credential, and routing
kubectl apply -f kubernetes/ingress/kong-plugins.yaml
kubectl apply -f kubernetes/ingress/kong-consumers.yaml
kubectl apply -f kubernetes/ingress/ingress.yaml

# Real TLS (optional, requires cert-manager installed - see the comments
# in kubernetes/cert-manager/cluster-issuer.yaml)
kubectl apply -f kubernetes/cert-manager/cluster-issuer.yaml
```

In this path there's no `kong.yml` to mount - Kong Ingress Controller
watches the `Ingress`/`KongPlugin`/`KongConsumer` objects continuously and
configures the (still DB-less) Kong data plane from them. The
`konghq.com/plugins` annotation on each `Ingress` in
`kubernetes/ingress/ingress.yaml` is the equivalent of a route's
`plugins:` block in `kong/kong.yml`; `KongClusterPlugin` with
`global: "true"` is the equivalent of `kong.yml`'s top-level `plugins:`
list.

## CI

`.github/workflows/ci.yaml` runs on every push/PR. What each job actually
checks (no step here is decorative or a stand-in for a check that doesn't
run):

| Job | What it does |
|---|---|
| `lint-kong-config` | Runs `kong config parse` against `kong/kong.yml` inside the real `kong:3.7` image - the same schema validation Kong itself uses on startup |
| `validate-compose` | `docker compose config --quiet` against `docker-compose.yml` |
| `validate-nginx-config` | Generates a cert, then runs `nginx -t` inside the real `nginx:1.27-alpine` image against `nginx/nginx.conf` + `conf.d/` |
| `validate-kubernetes-yaml` | `kubeconform` against every manifest under `kubernetes/`, explicitly skipping Kong's CRDs (`KongPlugin`, `KongClusterPlugin`, `KongConsumer`) since they have no public OpenAPI schema to validate against - the job doesn't pretend to check what it can't |
| `lint-helm-values` | `helm template` renders the real `kong/kong` chart with `kubernetes/kong/helm-values.yaml` and fails on schema errors |
| `e2e-smoke-test` | Actually builds and runs the full Compose stack, then curls through Nginx -> Kong -> backend and asserts: an unauthenticated request to the key-auth route gets `401`, an authenticated one succeeds, an unauthenticated request to `/api/orders` succeeds, and hammering `/api/orders` past its 5/minute limit gets a `429` |

## Security notes (read before reusing any of this)

- **The TLS certificate is self-signed**, generated by
  `scripts/generate-certs.sh` for local development. Replace it before any
  real deployment - see "TLS certificates" above.
- **The API key in `kong/kong.yml`, `kubernetes/ingress/kong-consumers.yaml`,
  and `.env.example` (`demo-key-CHANGE-ME-6f3a9c1d`) is a demo placeholder**,
  intentionally named so it's obvious if it ever ends up somewhere it
  shouldn't. It is safe to commit precisely because it's not a real
  credential for anything. Generate and manage a real one
  (`openssl rand -hex 24`, stored as a real secret, not in YAML in Git)
  before using key-auth for anything that matters.
- **CORS is wide open (`origins: ["*"]`)** in both the Kong declarative
  config and the Kubernetes `KongClusterPlugin`, to keep the demo
  frictionless from any client. Scope this to an explicit origin
  allow-list before production use.
- **Kong's Admin API** (`localhost:8001` in Compose, `ClusterIP` in the
  Helm values) is never routed through Nginx/the public listener and
  should stay that way - it has no authentication in front of it in this
  demo.
- **No secrets are hardcoded outside of clearly-labeled placeholders.**
  `.env` is gitignored; only `.env.example` (all placeholder values) is
  committed. `nginx/certs/` is gitignored except for a `.gitkeep`.
- Containers run as non-root users (`node`'s built-in `node` user,
  `reports-service`'s explicit `appuser`, `runAsNonRoot: true` in the k8s
  Deployments) with capabilities dropped in the Kubernetes manifests.

## What this project does *not* claim

This is a reference/demo architecture built to show real, working
Kong + Nginx configuration - it is not a load-tested production system,
and none of the services here do anything beyond return static/sample
data. There's no claim of throughput, latency, or scale numbers anywhere
in this repo, because none were measured.
