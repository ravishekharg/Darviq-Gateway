# -*- coding: utf-8 -*-
"""Generates Darviq_Gateway_High_Level_Design.docx from the docx_builder helper.
Run from the Docs/ directory (or anywhere, paths below are relative to this file).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docx_builder import DesignDoc

HERE = os.path.dirname(os.path.abspath(__file__))

doc = DesignDoc(
    project_name="Darviq Gateway",
    subtitle="Kong + Nginx API Gateway Reference Platform",
    doc_kind="High-Level Design (HLD)",
    version="1.0",
    date="July 31, 2026",
    status="Version 1.0",
)

doc.add_document_control()
doc.add_toc_field()

# ------------------------------------------------------------------
# 1. Introduction
# ------------------------------------------------------------------
doc.add_heading1("1. Introduction")

doc.add_heading2("1.1 Purpose")
doc.add_paragraph(
    "This document describes the high-level design of Darviq Gateway, a reference "
    "implementation of a layered API gateway. The repository demonstrates a production-style "
    "edge-security topology in which Nginx terminates TLS at the outer edge and Kong Gateway, "
    "running in DB-less/declarative mode, performs the actual API gateway work — routing, "
    "key-auth, rate-limiting, CORS, and structured access logging — in front of three minimal "
    "sample backend services. A parallel Kubernetes deployment path, using the Kong Ingress "
    "Controller and cert-manager, is also included as the intended production target. This "
    "document explains the components, their responsibilities, and how they interact, at a "
    "level suitable for an engineer evaluating or extending the reference architecture."
)

doc.add_heading2("1.2 Scope")
doc.add_paragraph("In scope for this document:")
doc.add_bullets([
    "The Docker Compose local-development topology: Nginx, Kong (DB-less), and the three sample services.",
    "The Kong declarative configuration (kong/kong.yml): services, routes, consumers, and plugins.",
    "The parallel Kubernetes path: Kong Ingress Controller via the official Helm chart, Ingress resources, "
    "KongPlugin/KongClusterPlugin/KongConsumer CRDs, and cert-manager for TLS.",
    "TLS termination, authentication, rate-limiting, and CORS as actually configured in this repository.",
    "The repository's own CI validation strategy, since it is part of what the reference demonstrates.",
])
doc.add_paragraph("Out of scope for this document:")
doc.add_bullets([
    "The internal business logic of the three sample services — they are intentionally trivial routing "
    "targets, not the point of the project.",
    "Any claim of measured throughput, latency, or capacity. None were measured; the repository's own README "
    "explicitly disclaims this.",
    "Operating a live Kubernetes cluster — the Kubernetes manifests are reviewed and schema-validated in CI "
    "but have not been applied against a live cluster as part of building this repository.",
    "Kong's Postgres/Cassandra-backed (non-DB-less) operating mode, which this repository does not use.",
])

doc.add_heading2("1.3 Intended audience")
doc.add_bullets([
    "Engineers evaluating this repository as a portfolio reference for edge/API-gateway architecture.",
    "Developers extending the reference (adding services, routes, or plugins).",
    "Reviewers assessing the design decisions (e.g., why both Nginx and Kong are present) before adapting "
    "the pattern to a real system.",
])

doc.add_heading2("1.4 Definitions & abbreviations")
doc.add_table(
    headers=["Term", "Definition"],
    rows=[
        ["TLS", "Transport Layer Security — encrypts traffic between clients and the Nginx edge."],
        ["Kong (DB-less)", "Kong Gateway operating mode where the entire routing/plugin configuration is "
         "loaded from a declarative file (kong.yml) or, in Kubernetes, from CRDs — no Postgres/Cassandra "
         "database is used."],
        ["Declarative configuration", "kong/kong.yml — the single file that fully describes Kong's services, "
         "routes, consumers, and plugins for the Compose path."],
        ["key-auth", "Kong plugin that requires a valid API key (via a configurable header) before a request "
         "is proxied to the upstream service."],
        ["rate-limiting", "Kong plugin that rejects requests exceeding a configured request count per time "
         "window (per-route, local/in-memory counters in this repository)."],
        ["CORS", "Cross-Origin Resource Sharing — the Kong `cors` plugin controls which browser origins, "
         "methods, and headers are permitted."],
        ["KIC", "Kong Ingress Controller — watches standard Kubernetes Ingress objects plus Kong CRDs and "
         "configures the Kong data plane continuously, replacing the mounted kong.yml file used in Compose."],
        ["CRD", "Custom Resource Definition — Kubernetes extension objects (KongPlugin, KongClusterPlugin, "
         "KongConsumer) used by KIC in place of kong.yml."],
        ["Consumer", "A Kong identity (here, `demo-consumer`) that credentials (an API key) are attached to."],
        ["Correlation ID", "A unique per-request identifier (X-Kong-Request-Id) injected by Kong's "
         "correlation-id plugin, used to trace one request across Nginx, Kong, and the upstream service."],
        ["Upstream / upstream service", "One of the three sample backend services (users-service, "
         "orders-service, reports-service) that Kong proxies requests to."],
    ],
)

# ------------------------------------------------------------------
# 2. System overview
# ------------------------------------------------------------------
doc.add_heading1("2. System overview")

doc.add_heading2("2.1 Problem statement")
doc.add_paragraph(
    "Production API estates typically separate two concerns at the network edge: (1) TLS termination and "
    "coarse, connection-level protection, which changes rarely and is usually owned by network/infrastructure "
    "teams, and (2) API-contract concerns — routing, authentication, rate-limiting, CORS, and observability — "
    "which change frequently as APIs evolve and are usually owned by application/platform teams. A common "
    "anti-pattern is to collapse both concerns into a single component, which either overloads a general-purpose "
    "reverse proxy with API-gateway logic it was not designed to express cleanly, or exposes a full API gateway's "
    "admin surface directly to the internet. Darviq Gateway demonstrates the layered alternative: a thin, "
    "well-understood edge (Nginx) in front of a purpose-built, declaratively configured API gateway (Kong), "
    "with a working local demonstration and a documented path to the equivalent Kubernetes-native topology."
)

doc.add_heading2("2.2 Proposed solution summary")
doc.add_paragraph(
    "The repository ships two deployment paths that implement the same routing/plugin story:"
)
doc.add_bullets([
    "Docker Compose (primary, fully working locally): Nginx terminates TLS on port 443 (mapped to host "
    "8443) and reverse-proxies plain HTTP to a Kong upstream block; Kong (kong:3.7, DB-less) reads "
    "kong/kong.yml and proxies to three backend containers over the internal Compose network.",
    "Kubernetes (reviewed, schema-validated in CI, not yet applied to a live cluster): the official Kong "
    "Helm chart deploys Kong Gateway with the Kong Ingress Controller enabled; standard Ingress objects plus "
    "KongPlugin/KongClusterPlugin/KongConsumer CRDs replace kong.yml as the source of configuration; "
    "cert-manager (Let's Encrypt) replaces the local self-signed-certificate script for real TLS.",
])
doc.add_paragraph(
    "In both paths, Kong's Admin API is never exposed on the public listener — only to the host (Compose, "
    "for local inspection) or as a ClusterIP (Kubernetes) — and every route is protected by at least a "
    "rate-limiting plugin, with the users-service route additionally requiring a valid API key via key-auth."
)

# ------------------------------------------------------------------
# 3. Architecture overview
# ------------------------------------------------------------------
doc.add_heading1("3. Architecture overview")

doc.add_table(
    headers=["Component", "Responsibility", "Technology"],
    rows=[
        ["Nginx edge", "TLS termination, HTTP->HTTPS redirect, reverse proxy and load-balancing to Kong, "
         "edge-level security headers, edge health check", "nginx:1.27-alpine"],
        ["Kong Gateway (DB-less)", "Routing, key-auth, rate-limiting, CORS, access logging, correlation IDs — "
         "driven entirely by a declarative file, no database", "kong:3.7"],
        ["users-service", "Sample authenticated upstream: list/get users", "Node.js 20 / Express"],
        ["orders-service", "Sample open (unauthenticated) upstream, tightly rate-limited: list/get orders", "Node.js 20 / Express"],
        ["reports-service", "Sample upstream with an intentionally slow endpoint used to exercise Kong's "
         "upstream timeouts: list/get reports, /slow", "Python 3.12 / FastAPI (uvicorn)"],
        ["Kong Ingress Controller (Kubernetes path)", "Watches Ingress + Kong CRDs and continuously "
         "configures the Kong data plane; replaces the mounted kong.yml", "Kong Ingress Controller (official Helm chart)"],
        ["cert-manager (Kubernetes path)", "Requests and renews real TLS certificates via Let's Encrypt "
         "ClusterIssuers", "cert-manager + Let's Encrypt (ACME)"],
        ["CI pipeline", "Validates every layer above against the real tooling that would validate it in "
         "production (Kong's own config parser, nginx -t, docker compose config, kubeconform, helm template) "
         "plus an end-to-end smoke test of the full Compose stack", "GitHub Actions"],
    ],
)

doc.add_heading2("3.1 Component descriptions")

doc.add_heading3("Nginx edge")
doc.add_paragraph(
    "Nginx is the only component with a public-facing port. It listens on 80 (redirects everything to HTTPS) "
    "and 443 (TLS, HTTP/2 enabled), terminating TLS with a certificate under nginx/certs/ and reverse-proxying "
    "everything under /api/ to an `upstream kong_upstream` block over plain HTTP inside the Docker network. "
    "That upstream block is also the designed scale-out point: it already round-robins across every `server` "
    "line listed there, so adding Kong replicas is a one-line config change with no application changes."
)

doc.add_heading3("Kong Gateway (DB-less)")
doc.add_paragraph(
    "Kong runs with KONG_DATABASE=off and loads its entire configuration from kong/kong.yml "
    "(KONG_DECLARATIVE_CONFIG). This means the full routing/plugin topology is a single reviewable file with "
    "no Admin-API writes required to reproduce a deployment — a GitOps-friendly model by construction. Kong's "
    "proxy port (8000) and Admin API (8001) are only reachable from Nginx and the host respectively; neither "
    "is exposed on the public listener."
)

doc.add_heading3("Sample backend services")
doc.add_paragraph(
    "users-service and orders-service are near-identical minimal Express apps (GET /, GET /:id, GET /health); "
    "reports-service is a FastAPI app with the same shape plus an intentionally slow GET /slow endpoint "
    "(~5 second sleep) used to demonstrate Kong's upstream read_timeout behavior. All three set an "
    "X-Upstream-Service response header and echo the path they actually received, so a caller can verify a "
    "request genuinely traversed Nginx -> Kong -> the correct upstream rather than being served by a mock."
)

doc.add_heading3("Kong Ingress Controller path (Kubernetes)")
doc.add_paragraph(
    "In Kubernetes, the official kong/kong Helm chart deploys Kong Gateway with ingressController.enabled: "
    "true. There is no kong.yml to mount in this path — standard Ingress resources (annotated with "
    "konghq.com/plugins) plus KongPlugin/KongClusterPlugin/KongConsumer CRDs are watched continuously by the "
    "controller and used to configure the still-DB-less Kong data plane. Nginx itself is not part of this "
    "path; a cloud load balancer (or optionally ingress-nginx as a second edge layer) fills that role instead."
)

# ------------------------------------------------------------------
# 4. End-to-end functional workflow
# ------------------------------------------------------------------
doc.add_heading1("4. End-to-end functional workflow")
doc.add_figure_placeholder(
    "Figure 4.1 — Request flow: Client -> Nginx (TLS termination, port 8443) -> Kong upstream block -> "
    "Kong (route match, key-auth if configured, rate-limiting, CORS, correlation-id, file-log) -> backend "
    "service (users-service / orders-service / reports-service) -> response traverses back through Kong and "
    "Nginx to the client"
)
doc.add_paragraph(
    "A client request to, for example, https://localhost:8443/api/users follows this path:"
)
doc.add_bullets([
    "1. The client opens a TLS connection to Nginx on port 443 (host-mapped to 8443). Nginx terminates TLS "
    "using the self-signed certificate at nginx/certs/gateway.crt (or a real certificate in production).",
    "2. Nginx's location /api/ block reverse-proxies the decrypted HTTP request to the kong_upstream block "
    "(currently a single kong:8000 entry), forwarding Host, X-Real-IP, X-Forwarded-For, and X-Forwarded-Proto.",
    "3. Kong matches the request against a route in kong/kong.yml by path prefix (e.g. /api/users) and, "
    "because strip_path: true, forwards to the upstream with that prefix removed.",
    "4. Kong evaluates the route's plugins in order: key-auth (users-route only — rejects with 401 if no/"
    "invalid apikey header), rate-limiting (every route — rejects with 429 if the per-minute counter is "
    "exceeded), plus the global plugins cors, correlation-id, and file-log that apply to every request "
    "regardless of route.",
    "5. If the request passes, Kong proxies it to the matching backend service's container (e.g. "
    "http://users-service:3001/) using each service's own connect/read/write timeouts.",
    "6. The backend service responds, setting X-Upstream-Service so the response can be verified as having "
    "reached the real upstream; Kong adds X-Kong-Request-Id, X-Kong-Upstream-Latency/X-Kong-Proxy-Latency, "
    "and X-RateLimit-* headers before the response traverses back through Nginx to the client.",
])

# ------------------------------------------------------------------
# 5. Module-wise design overview
# ------------------------------------------------------------------
doc.add_heading1("5. Module-wise design overview")

doc.add_heading2("5.1 Nginx TLS/edge configuration (nginx/)")
doc.add_paragraph(
    "nginx/nginx.conf sets global directives (worker_processes auto, a custom gateway_edge log format "
    "capturing status/bytes/request time/upstream time, and includes conf.d/*.conf). nginx/conf.d/gateway.conf "
    "defines the kong_upstream block, an HTTP (port 80) server that only issues a 301 redirect to HTTPS, and "
    "the main HTTPS (port 443, HTTP/2) server that terminates TLS, sets HSTS/X-Content-Type-Options/"
    "X-Frame-Options headers, caps client_max_body_size at 5m, proxies /api/ to Kong, and serves a local "
    "/healthz edge health check that does not traverse Kong."
)

doc.add_heading2("5.2 Kong declarative configuration and plugins (kong/kong.yml)")
doc.add_paragraph(
    "A single _format_version: \"3.0\" file defining three services (users-service, orders-service, "
    "reports-service), one route per service, one demo consumer with a key-auth credential, and both "
    "route-scoped and global plugins. This is the sole source of truth for Kong's behavior in the Compose "
    "path — editing it and running `docker compose exec kong kong reload` is the entire config-change workflow."
)

doc.add_heading2("5.3 Sample backend services (services/)")
doc.add_paragraph(
    "Three intentionally minimal services acting purely as routing targets: users-service and orders-service "
    "(Node 20/Express, near-identical shape, in-memory arrays of demo data), and reports-service (Python "
    "3.12/FastAPI/uvicorn, with the added /slow endpoint). Each has its own Dockerfile running as a non-root "
    "user (node's built-in node user; reports-service's explicit appuser) and a Docker Compose healthcheck."
)

doc.add_heading2("5.4 Kubernetes / Kong Ingress Controller path (kubernetes/)")
doc.add_paragraph(
    "A parallel manifest set: namespace.yaml (gateway-demo namespace), backend-services/ (a Deployment + "
    "Service per sample service, 2 replicas each, readiness/liveness probes on /health, resource requests/"
    "limits, runAsNonRoot with all capabilities dropped), kong/helm-values.yaml (values for the official "
    "kong/kong Helm chart — DB-less, KIC enabled, Admin API kept ClusterIP-only, proxy exposed as a "
    "LoadBalancer Service, 2 Kong replicas), ingress/ (Ingress objects plus KongPlugin/KongClusterPlugin/"
    "KongConsumer CRDs mirroring kong.yml's routes, plugins, and consumer), and cert-manager/ "
    "(ClusterIssuer examples for Let's Encrypt staging and production, using the HTTP-01 challenge)."
)

doc.add_heading2("5.5 Certificate generation and CI validation (scripts/, .github/)")
doc.add_paragraph(
    "scripts/generate-certs.sh generates a local self-signed certificate (SHA-256, 2048-bit RSA, 365-day "
    "validity, SANs for localhost/nginx/127.0.0.1) for the Nginx edge, explicitly for local development only. "
    ".github/workflows/ci.yaml runs six jobs on every push/PR, each exercising the real tool that would "
    "validate that layer in production (Kong's own `kong config parse`, `nginx -t`, `docker compose config`, "
    "kubeconform, `helm template`), plus an end-to-end smoke test that builds the full Compose stack and "
    "asserts real HTTP behavior (401 without a key, success with the demo key, a 429 after exceeding the "
    "orders-service rate limit)."
)

# ------------------------------------------------------------------
# 6. Data design (adapted: Configuration model)
# ------------------------------------------------------------------
doc.add_heading1("6. Data design (configuration model)")
doc.add_paragraph(
    "This repository has no application database or persistent data store — Kong itself runs DB-less, and "
    "the sample services hold only small in-memory arrays. The closest analogue to a data model is Kong's "
    "declarative configuration structure, which is either a single YAML file (Compose path) or a set of "
    "Kubernetes objects (Kubernetes path) describing the same four entity types:"
)
doc.add_table(
    headers=["Entity", "Compose representation (kong.yml)", "Kubernetes representation"],
    rows=[
        ["Service", "services: — name, url, connect/read/write timeouts", "Implicit: Ingress backend.service "
         "pointing at a Kubernetes Service"],
        ["Route", "routes: (nested under a service) — name, paths, strip_path, methods", "Ingress rule "
         "(path, pathType, backend)"],
        ["Plugin (route-scoped)", "plugins: nested under a route", "KongPlugin object + "
         "konghq.com/plugins annotation on the Ingress"],
        ["Plugin (global)", "top-level plugins: list", "KongClusterPlugin with label global: \"true\""],
        ["Consumer", "consumers: — username + keyauth_credentials", "KongConsumer object + a referenced "
         "Kubernetes Secret (konghq.com/credential: key-auth)"],
    ],
)
doc.add_paragraph(
    "The consumer/credential model is intentionally minimal: a single demo-consumer with one key-auth "
    "credential (demo-key-CHANGE-ME-6f3a9c1d), used only to protect the users-service route. It is a "
    "clearly-labeled placeholder in both representations, safe to commit precisely because it is not a real "
    "credential."
)

# ------------------------------------------------------------------
# 7. Technology stack
# ------------------------------------------------------------------
doc.add_heading1("7. Technology stack")
doc.add_table(
    headers=["Layer", "Technology", "Notes"],
    rows=[
        ["Edge / TLS termination", "Nginx 1.27 (alpine)", "Only publicly reachable component; HTTP/2, "
         "TLS 1.2/1.3"],
        ["API gateway", "Kong Gateway 3.7, DB-less", "No Postgres/Cassandra dependency; config from kong.yml "
         "or CRDs"],
        ["Kong plugins used", "key-auth, rate-limiting, cors, file-log, correlation-id", "All bundled "
         "open-source Kong plugins — no custom/Lua plugin code"],
        ["Sample service (users, orders)", "Node.js 20 (alpine) / Express", "Minimal REST endpoints, "
         "non-root container user"],
        ["Sample service (reports)", "Python 3.12 (slim) / FastAPI + uvicorn", "Includes one deliberately "
         "slow endpoint"],
        ["Local orchestration", "Docker Compose", "Single docker-compose.yml, one bridge network"],
        ["Production/K8s orchestration", "Kubernetes + Helm (official kong/kong chart)", "Reviewed and "
         "schema-validated in CI, not yet applied to a live cluster"],
        ["Ingress control plane (K8s)", "Kong Ingress Controller", "Watches Ingress + Kong CRDs continuously"],
        ["TLS in Kubernetes", "cert-manager + Let's Encrypt (ACME, HTTP-01)", "Staging and production "
         "ClusterIssuer examples provided"],
        ["CI/CD", "GitHub Actions", "kong config parse, nginx -t, docker compose config, kubeconform, "
         "helm template, full Compose e2e smoke test"],
    ],
)

# ------------------------------------------------------------------
# 8. Deployment architecture
# ------------------------------------------------------------------
doc.add_heading1("8. Deployment architecture")
doc.add_figure_placeholder(
    "Figure 8.1 — Two parallel deployment targets: (left) Docker Compose — Nginx + Kong + 3 services on a "
    "single bridge network, host ports 8080/8443/8001; (right) Kubernetes — cloud LoadBalancer/Ingress -> "
    "Kong Gateway + Kong Ingress Controller (Helm) -> backend Deployments/Services in the gateway-demo "
    "namespace, with cert-manager issuing TLS certificates"
)
doc.add_paragraph(
    "Docker Compose path: five containers on one bridge network (gateway-net) — users-service, "
    "orders-service, reports-service, kong, and nginx. Kong depends on all three backend healthchecks passing "
    "before starting; Nginx depends on Kong's healthcheck. Only Nginx's ports (80, 443) and Kong's Admin API "
    "port (8001, host-only, for local inspection) are published to the host; every other port is only "
    "reachable inside the Compose network."
)
doc.add_paragraph(
    "Kubernetes path: `helm install kong kong/kong` deploys Kong Gateway plus the Kong Ingress Controller "
    "into the gateway-demo namespace (DB-less, 2 replicas, Admin API kept ClusterIP, proxy exposed as a "
    "LoadBalancer Service). Backend Deployments (2 replicas each, readiness/liveness probes, resource "
    "limits, non-root/no-capabilities security contexts) and Services are applied from "
    "kubernetes/backend-services/. Routing and plugins are applied via kubernetes/ingress/ (Ingress objects, "
    "KongPlugin/KongClusterPlugin, KongConsumer + Secret). TLS is optionally completed via cert-manager "
    "ClusterIssuers in kubernetes/cert-manager/. As the README notes, this path has been reviewed and "
    "schema-validated (kubeconform, helm template) in CI but not applied against a live cluster while "
    "building this repository — it should be treated as a solid, validated starting point rather than a "
    "battle-tested deployment."
)
doc.add_table(
    headers=["Variable / setting", "Where", "Purpose"],
    rows=[
        ["NGINX_HTTP_HOST_PORT", ".env / docker-compose.yml (default 8080)", "Host port for Nginx's HTTP "
         "(redirect-only) listener"],
        ["NGINX_HTTPS_HOST_PORT", ".env / docker-compose.yml (default 8443)", "Host port for Nginx's HTTPS "
         "(TLS) listener — the port used for all real requests"],
        ["KONG_ADMIN_HOST_PORT", ".env / docker-compose.yml (default 8001)", "Host port for Kong's Admin "
         "API — local inspection only, never routed through Nginx"],
        ["DEMO_API_KEY", ".env.example", "Reference copy of the demo key-auth credential for curl examples; "
         "does not itself configure Kong — kong/kong.yml is authoritative"],
        ["KONG_DATABASE", "docker-compose.yml environment (kong service) = \"off\"", "Selects Kong's DB-less "
         "declarative mode"],
        ["KONG_DECLARATIVE_CONFIG", "docker-compose.yml environment (kong service)", "Path inside the "
         "container (/kong/declarative/kong.yml) that kong.yml is mounted to"],
        ["ingressController.enabled / installCRDs", "kubernetes/kong/helm-values.yaml", "Enables Kong "
         "Ingress Controller; CRDs installed separately/once per cluster"],
    ],
)

# ------------------------------------------------------------------
# 9. Security design
# ------------------------------------------------------------------
doc.add_heading1("9. Security design")

doc.add_heading2("9.1 TLS termination")
doc.add_paragraph(
    "Nginx terminates TLS using a certificate at nginx/certs/gateway.crt / gateway.key, generated locally by "
    "scripts/generate-certs.sh for development (self-signed, RSA-2048, SHA-256, 365-day validity, SANs "
    "localhost/nginx/127.0.0.1 — explicitly not for real use). The listener restricts protocols to "
    "ssl_protocols TLSv1.2 TLSv1.3 with ssl_ciphers HIGH:!aNULL:!MD5 and ssl_prefer_server_ciphers on. "
    "Strict-Transport-Security (max-age=63072000), X-Content-Type-Options: nosniff, and X-Frame-Options: DENY "
    "are added on every response. For real deployments the README documents three concrete replacement paths: "
    "terminate at a cloud load balancer with a managed certificate, obtain a certbot/Let's Encrypt certificate "
    "on a VM, or use cert-manager in Kubernetes (kubernetes/cert-manager/cluster-issuer.yaml)."
)

doc.add_heading2("9.2 Authentication (key-auth credential model)")
doc.add_paragraph(
    "Only the /api/users route requires authentication, via Kong's key-auth plugin configured with "
    "key_names: [apikey] and hide_credentials: true (the header is stripped before the request reaches "
    "users-service). The one demo consumer (demo-consumer) has a single key-auth credential "
    "(demo-key-CHANGE-ME-6f3a9c1d), duplicated — and clearly labeled as a placeholder — in kong/kong.yml, "
    "kubernetes/ingress/kong-consumers.yaml, and .env.example. Both the README and the config comments are "
    "explicit that this key must be regenerated (openssl rand -hex 24) and stored as a real secret before "
    "key-auth is used for anything that matters."
)

doc.add_heading2("9.3 Rate limiting")
doc.add_paragraph(
    "Every route has its own rate-limiting plugin instance using policy: local (in-memory, per-Kong-node "
    "counters — appropriate for a single-instance demo, but note this is not centrally counted across "
    "multiple Kong replicas) and fault_tolerant: true. Configured thresholds: users-service 20 requests/"
    "minute, orders-service 5 requests/minute (deliberately tight so the README's curl walkthrough can trip "
    "a 429 in a handful of requests), reports-service 10 requests/minute. Kong returns HTTP 429 once a "
    "route's per-minute counter is exceeded and exposes X-RateLimit-* headers (hide_client_headers: false) "
    "so callers can see their remaining quota."
)

doc.add_heading2("9.4 CORS policy")
doc.add_paragraph(
    "A single global cors plugin applies to every route: origins: [\"*\"] (any origin permitted), methods "
    "GET/POST/OPTIONS, allowed headers Accept/Content-Type/apikey, exposed headers X-Upstream-Service and "
    "X-RateLimit-Remaining-Minute, credentials: false, max_age: 3600. The repository's own README explicitly "
    "flags origins: [\"*\"] as a deliberate demo convenience that must be scoped to an explicit origin "
    "allow-list before any production use."
)

doc.add_heading2("9.5 Network exposure and defense in depth")
doc.add_bullets([
    "Kong's proxy port (8000) is never exposed to clients directly — only Nginx reaches it, over the internal "
    "Docker network (Compose) or ClusterIP-equivalent internal routing (Kubernetes).",
    "Kong's Admin API (8001) has no authentication in front of it in this demo and is published to the host "
    "for local inspection only (Compose) or kept ClusterIP (Kubernetes Helm values) — it must never be "
    "reachable from outside the host/cluster network in a real deployment.",
    "All three sample-service containers run as non-root users (node's built-in node user; reports-service's "
    "explicit appuser); the Kubernetes Deployments additionally set runAsNonRoot: true, "
    "allowPrivilegeEscalation: false, and drop all Linux capabilities.",
    "No secrets are hardcoded outside clearly-labeled placeholders; .env is gitignored (only .env.example, "
    "all placeholder values, is committed) and nginx/certs/ is gitignored except for a .gitkeep.",
])

# ------------------------------------------------------------------
# 10. Non-functional requirements
# ------------------------------------------------------------------
doc.add_heading1("10. Non-functional requirements")
doc.add_paragraph(
    "The repository is explicit that it makes no throughput/latency/scale claims — none were measured. The "
    "table below describes the approach/target this reference actually implements, not a benchmarked figure."
)
doc.add_table(
    headers=["Attribute", "Target / approach in this repository"],
    rows=[
        ["Availability", "Not applicable at demo scale (single Kong instance, single replica per backend in "
         "Compose). Kubernetes path runs 2 replicas of Kong and 2 replicas of each backend Deployment with "
         "readiness/liveness probes."],
        ["Scalability", "Nginx's upstream block is designed to round-robin across multiple Kong replicas by "
         "adding one server line — no application change required; the Helm values already set "
         "replicaCount: 2 for Kong."],
        ["Latency overhead (edge + gateway)", "Not measured/benchmarked (explicitly disclaimed in the "
         "README). Contributing factors present in config: Nginx proxy timeouts (connect 5s / send 10s / "
         "read 10s) and Kong per-service timeouts (2s connect for all three services; 5s read/write for "
         "users-service and orders-service; 3s read/write for reports-service)."],
        ["Rate-limit thresholds", "users-service 20/min, orders-service 5/min, reports-service 10/min "
         "(policy: local, per-Kong-node counters)."],
        ["Timeout handling", "reports-service's Kong route uses a 3000ms read_timeout, intentionally shorter "
         "than the /slow endpoint's ~5s sleep, so Kong returns 504 independently of any client or Nginx "
         "timeout — a deliberate demonstration of upstream-timeout behavior, not a production SLA."],
        ["Observability", "Every request gets a correlation ID (X-Kong-Request-Id) and Kong emits structured "
         "access logs (file-log plugin, to stdout) plus latency headers (X-Kong-Upstream-Latency, "
         "X-Kong-Proxy-Latency); Nginx uses a custom log format capturing status/bytes/request and upstream "
         "response time."],
        ["Security posture", "TLS 1.2/1.3 only, HSTS enabled, key-auth on the sensitive route, global "
         "rate-limiting and CORS, Admin API never on the public listener, non-root containers throughout."],
        ["CI validation coverage", "Every config layer is validated against its real tool (Kong's own config "
         "parser, nginx -t, docker compose config, kubeconform, helm template) plus a full end-to-end smoke "
         "test of the Compose stack on every push/PR."],
    ],
)

# ------------------------------------------------------------------
# 11. Assumptions & constraints
# ------------------------------------------------------------------
doc.add_heading1("11. Assumptions & constraints")
doc.add_bullets([
    "This is a demo/reference architecture built for a portfolio, not a production deployment — stated "
    "directly in the README.",
    "The backend services are intentionally trivial (static/sample in-memory data) — their purpose is to "
    "prove requests traverse the real chain, not to model a real domain.",
    "The Kubernetes manifests have been reviewed and schema-validated in CI (kubeconform, helm template) but "
    "have not been applied against a live cluster while building this repository, since no cluster was "
    "available in that environment.",
    "The TLS certificate used locally is self-signed and must be replaced before any real deployment; three "
    "concrete replacement paths are documented (cloud LB, certbot, cert-manager).",
    "The demo API key and all placeholder credentials are intentionally non-secret and safe to commit; a "
    "real deployment must generate and manage real credentials outside of version control.",
    "Kong's rate-limiting uses policy: local (in-memory per-node counters), which is correct for a "
    "single-instance demo but would need a shared counter (e.g. policy: redis) to be accurate across multiple "
    "Kong replicas in a real horizontally-scaled deployment.",
    "CORS is deliberately wide open (origins: [\"*\"]) for demo friction-lessness and is explicitly flagged "
    "as something to scope down before production use.",
])

# ------------------------------------------------------------------
# 12. Future enhancements
# ------------------------------------------------------------------
doc.add_heading1("12. Future enhancements")
doc.add_bullets([
    "Apply the Kubernetes manifests against a real cluster (kind/minikube or a cloud cluster) and record the "
    "actual `helm install` / `kubectl apply` outcomes, closing the gap between \"schema-validated\" and "
    "\"proven to run\".",
    "Switch rate-limiting's policy from local to a shared backend (e.g. redis) once more than one Kong "
    "replica is actually running, so limits are enforced consistently across replicas rather than per-node.",
    "Scope the CORS policy from a wildcard origin to an explicit allow-list, as the README itself calls out.",
    "Replace the local self-signed certificate and the demo API key with real, securely-managed credentials "
    "(a real cert via cert-manager/certbot; a generated key stored in a secret manager) before any real use.",
    "Add a second Kong replica in the Compose stack itself (the Nginx upstream block already supports this "
    "with one added line) to demonstrate the load-balancing behavior end-to-end, not just document it.",
    "Consider adding authenticated route coverage for orders-service and reports-service (currently open) if "
    "the demo were extended to model a more realistic authorization posture.",
    "Add real latency/throughput measurements if the repository's purpose ever expands beyond a "
    "configuration reference, replacing the current explicit \"not measured\" disclaimer with actual numbers.",
])

# ------------------------------------------------------------------
# 13. Appendix
# ------------------------------------------------------------------
doc.add_heading1("13. Appendix")

doc.add_heading2("13.1 References")
doc.add_bullets([
    "Repository README.md (root) — architecture diagram, run instructions, security notes, and explicit "
    "non-claims section.",
    "kong/kong.yml — Kong declarative configuration (services, routes, consumers, plugins).",
    "nginx/nginx.conf and nginx/conf.d/gateway.conf — Nginx edge configuration.",
    "docker-compose.yml and .env.example — local stack topology and configuration.",
    "kubernetes/ (namespace.yaml, backend-services/, kong/helm-values.yaml, ingress/, cert-manager/) — "
    "Kubernetes/Kong Ingress Controller deployment path.",
    ".github/workflows/ci.yaml — CI validation strategy.",
    "Kong Gateway documentation — https://docs.konghq.com/gateway/",
    "Kong Ingress Controller documentation — https://docs.konghq.com/kubernetes-ingress-controller/",
    "cert-manager documentation — https://cert-manager.io/docs/",
])

doc.add_heading2("13.2 Change history")
doc.add_table(
    headers=["Version", "Date", "Description"],
    rows=[
        ["1.0", "July 31, 2026", "Initial high-level design document"],
    ],
)

doc.save(os.path.join(HERE, "Darviq_Gateway_High_Level_Design.docx"))
print("Wrote Darviq_Gateway_High_Level_Design.docx")
