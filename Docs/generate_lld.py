# -*- coding: utf-8 -*-
"""Generates Darviq_Gateway_Low_Level_Design.docx from the docx_builder helper."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docx_builder import DesignDoc

HERE = os.path.dirname(os.path.abspath(__file__))

doc = DesignDoc(
    project_name="Darviq Gateway",
    subtitle="Kong + Nginx API Gateway Reference Platform",
    doc_kind="Low-Level Design (LLD)",
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
    "This Low-Level Design (LLD) document provides the concrete, file-level detail behind the architecture "
    "described in Darviq_Gateway_High_Level_Design.docx (v1.0). Where the HLD describes components and their "
    "responsibilities, this document cites the actual configuration files, directive values, Kong plugin "
    "configurations, and sample-service endpoints that implement them, so a reader can locate and modify the "
    "exact line of configuration responsible for any given behavior."
)

doc.add_heading2("1.2 Scope")
doc.add_paragraph(
    "This document covers the concrete implementation of every module listed in HLD section 5: the Nginx "
    "edge configuration, the Kong declarative configuration and plugins, the three sample backend services, "
    "the Kubernetes/Kong Ingress Controller path, and certificate generation/CI validation. It does not "
    "repeat the rationale already covered in the HLD (e.g. why Nginx and Kong are layered) except where "
    "needed to explain a specific configuration value."
)

doc.add_heading2("1.3 References")
doc.add_bullets([
    "Darviq_Gateway_High_Level_Design.docx (v1.0) — architecture overview this document elaborates on.",
    "kong/kong.yml — Kong DB-less declarative configuration.",
    "nginx/nginx.conf, nginx/conf.d/gateway.conf — Nginx edge configuration.",
    "services/users-service/app.js, services/orders-service/app.js, services/reports-service/app.py — "
    "sample backend service implementations.",
    "docker-compose.yml, .env.example — local stack topology and configuration.",
    "kubernetes/namespace.yaml, kubernetes/backend-services/*.yaml, kubernetes/kong/helm-values.yaml, "
    "kubernetes/ingress/*.yaml, kubernetes/cert-manager/cluster-issuer.yaml — Kubernetes deployment path.",
    "scripts/generate-certs.sh — local TLS certificate generation.",
    ".github/workflows/ci.yaml — CI validation jobs.",
])

# ------------------------------------------------------------------
# 2. Detailed module design
# ------------------------------------------------------------------
doc.add_heading1("2. Detailed module design")

doc.add_heading2("2.1 Nginx TLS/edge configuration")
doc.add_paragraph("File: nginx/nginx.conf")
doc.add_bullets([
    "worker_processes auto; events { worker_connections 1024; }",
    "Custom log format gateway_edge: '$remote_addr - [$time_local] \"$request\" status=$status "
    "bytes=$body_bytes_sent rt=$request_time upstream_rt=$upstream_response_time referrer=\"$http_referer\" "
    "ua=\"$http_user_agent\"' — written to /var/log/nginx/access.log; errors logged at warn level.",
    "include /etc/nginx/conf.d/*.conf; pulls in gateway.conf.",
])
doc.add_paragraph("File: nginx/conf.d/gateway.conf")
doc.add_bullets([
    "upstream kong_upstream { server kong:8000 max_fails=3 fail_timeout=10s; keepalive 32; } — one Kong "
    "replica today; additional server lines round-robin automatically, no application change needed.",
    "server { listen 80; } — the only action is `return 301 https://$host:8443$request_uri;`; nothing is "
    "proxied over plain HTTP.",
    "server { listen 443 ssl; http2 on; } — the main edge server. TLS: ssl_certificate "
    "/etc/nginx/certs/gateway.crt, ssl_certificate_key /etc/nginx/certs/gateway.key, "
    "ssl_protocols TLSv1.2 TLSv1.3, ssl_ciphers HIGH:!aNULL:!MD5, ssl_prefer_server_ciphers on, "
    "ssl_session_cache shared:SSL:10m, ssl_session_timeout 10m.",
    "Security headers on every response: Strict-Transport-Security \"max-age=63072000\" always; "
    "X-Content-Type-Options \"nosniff\" always; X-Frame-Options \"DENY\" always.",
    "client_max_body_size 5m; — request body size cap enforced at the edge.",
    "location /api/ { proxy_pass http://kong_upstream; proxy_http_version 1.1; } forwards Host, X-Real-IP, "
    "X-Forwarded-For, X-Forwarded-Proto, and clears the Connection header for keepalive reuse. Timeouts: "
    "proxy_connect_timeout 5s, proxy_send_timeout 10s, proxy_read_timeout 10s.",
    "location = /healthz returns a static 200 {\"status\":\"ok\",\"component\":\"nginx-edge\"} without "
    "traversing Kong, with access_log off.",
    "location / (catch-all) returns 404 {\"error\":\"not found - all routes are served under /api/\"}.",
])

doc.add_heading2("2.2 Kong declarative configuration and plugins")
doc.add_paragraph("File: kong/kong.yml (_format_version: \"3.0\", _transform: true)")
doc.add_paragraph(
    "Three services are declared, each with its own connect/read/write timeouts and exactly one route:"
)
doc.add_table(
    headers=["Service", "url", "connect_timeout", "read_timeout", "write_timeout", "Route path", "strip_path", "methods"],
    rows=[
        ["users-service", "http://users-service:3001", "2000", "5000", "5000", "/api/users", "true", "GET"],
        ["orders-service", "http://orders-service:3002", "2000", "5000", "5000", "/api/orders", "true", "GET"],
        ["reports-service", "http://reports-service:8000", "2000", "3000", "3000", "/api/reports", "true", "GET"],
    ],
)
doc.add_paragraph(
    "Route-scoped plugins: users-route has key-auth (config.key_names: [apikey], hide_credentials: true) "
    "followed by rate-limiting (config.minute: 20, policy: local, fault_tolerant: true, "
    "hide_client_headers: false). orders-route has only rate-limiting (config.minute: 5, same policy/"
    "fault_tolerant/hide_client_headers values) — deliberately tight so the README's curl loop can trip a "
    "429 within 6 requests. reports-route has only rate-limiting (config.minute: 10, same values)."
)
doc.add_paragraph(
    "Consumer: demo-consumer, with one keyauth_credentials entry, key: demo-key-CHANGE-ME-6f3a9c1d "
    "(clearly labeled placeholder, safe to commit)."
)
doc.add_paragraph(
    "Global plugins (apply to every route regardless of service):"
)
doc.add_bullets([
    "cors: origins [\"*\"], methods [GET, POST, OPTIONS], headers [Accept, Content-Type, apikey], "
    "exposed_headers [X-Upstream-Service, X-RateLimit-Remaining-Minute], credentials: false, max_age: 3600.",
    "file-log: path /dev/stdout, reopen: false — every proxied request logged to stdout, visible via "
    "`docker compose logs kong`.",
    "correlation-id: header_name X-Kong-Request-Id, generator: uuid, echo_downstream: true — a fresh UUID "
    "per request, echoed back to the client.",
])
doc.add_paragraph(
    "Operational note: config changes are applied by editing kong.yml and running "
    "`docker compose exec kong kong reload` (no Admin API write, no restart required for a reload)."
)

doc.add_heading2("2.3 Sample backend services")
doc.add_paragraph("services/users-service/app.js (Node.js/Express, PORT default 3001)")
doc.add_bullets([
    "Sets X-Upstream-Service: users-service on every response via middleware.",
    "GET /health — unauthenticated, used by the Compose healthcheck; not routed through Kong's key-auth.",
    "GET / — returns { service, upstream, receivedPath, count, users: [...] } from an in-memory USERS array "
    "of 3 records (Asha Rao/admin, Priya Nair/viewer, Marcus Chen/editor).",
    "GET /:id — returns a single user by numeric id or 404 { error: \"user not found\" }.",
    "Catch-all — 404 { error: \"not found\", path }.",
    "Because Kong's users-route has strip_path: true, a client call to /api/users arrives here as GET /.",
])
doc.add_paragraph("services/orders-service/app.js (Node.js/Express, PORT default 3002)")
doc.add_bullets([
    "Same shape as users-service: X-Upstream-Service: orders-service header, GET /health, GET / (returns "
    "an in-memory ORDERS array of 3 records: Wireless Mouse/shipped, Mechanical Keyboard/processing, "
    "USB-C Hub/delivered), GET /:id, 404 catch-all.",
])
doc.add_paragraph("services/reports-service/app.py (Python/FastAPI + uvicorn, port 8000)")
doc.add_bullets([
    "Sets X-Upstream-Service: reports-service via an @app.middleware(\"http\") hook.",
    "GET /health — status/service JSON.",
    "GET / — returns an in-memory REPORTS list of 2 records (rpt-2026-q1, rpt-2026-q2).",
    "GET /slow — declared before /{report_id} so it is not shadowed by the catch-all; performs "
    "await asyncio.sleep(5) (~5s) and returns elapsedSeconds — used to exercise Kong's "
    "reports-route read_timeout: 3000ms, which causes Kong to return 504 before the 5s sleep completes.",
    "GET /{report_id} — returns a matching report or a 404 JSONResponse.",
])

doc.add_heading2("2.4 Kubernetes / Kong Ingress Controller path")
doc.add_paragraph("kubernetes/namespace.yaml — creates the gateway-demo namespace.")
doc.add_paragraph(
    "kubernetes/backend-services/{users,orders,reports}-service.yaml — one Deployment + Service per sample "
    "service. Each Deployment: replicas: 2, readinessProbe and livenessProbe both on GET /health (readiness "
    "initialDelaySeconds 3 / periodSeconds 10; liveness initialDelaySeconds 5 / periodSeconds 15), resources "
    "requests cpu 50m/memory 64Mi and limits cpu 200m/memory 128Mi, securityContext runAsNonRoot: true, "
    "allowPrivilegeEscalation: false, capabilities.drop: [\"ALL\"]. Image field is a REPLACE_ME_REGISTRY "
    "placeholder — not a real pushed image."
)
doc.add_paragraph(
    "kubernetes/kong/helm-values.yaml — values for the official kong/kong Helm chart: image kong:3.7, "
    "env.database: \"off\" (DB-less), proxy/admin access+error logs to stdout/stderr, postgresql.enabled: "
    "false, ingressController.enabled: true (installCRDs: false — CRDs installed once, separately), "
    "admin.type: ClusterIP (never exposed outside the cluster), proxy.type: LoadBalancer with both "
    "http (port 80) and tls (port 443) enabled (tls.secretName commented out until a cert-manager Secret "
    "exists), resources requests cpu 200m/memory 256Mi and limits cpu 500m/memory 512Mi, replicaCount: 2."
)
doc.add_paragraph(
    "kubernetes/ingress/ingress.yaml — one Ingress per service, ingressClassName: kong, "
    "konghq.com/strip-path: \"true\", and a konghq.com/plugins annotation naming the route-scoped "
    "KongPlugin objects to attach: users-service -> key-auth-users,rate-limiting-users; orders-service -> "
    "rate-limiting-orders; reports-service -> rate-limiting-reports. Paths mirror the Compose routes exactly "
    "(/api/users, /api/orders, /api/reports)."
)
doc.add_paragraph(
    "kubernetes/ingress/kong-plugins.yaml — KongPlugin objects key-auth-users (key_names: [apikey], "
    "hide_credentials: true), rate-limiting-users (minute: 20), rate-limiting-orders (minute: 5), "
    "rate-limiting-reports (minute: 10), all policy: local / fault_tolerant: true; plus three "
    "KongClusterPlugin objects labeled global: \"true\" — cors-global, file-log-global, "
    "correlation-id-global — with config identical to kong.yml's global plugins section."
)
doc.add_paragraph(
    "kubernetes/ingress/kong-consumers.yaml — a Secret demo-consumer-apikey (labeled "
    "konghq.com/credential: key-auth, stringData.key: demo-key-CHANGE-ME-6f3a9c1d — the same demo "
    "placeholder used elsewhere) referenced by a KongConsumer object named demo-consumer."
)
doc.add_paragraph(
    "kubernetes/cert-manager/cluster-issuer.yaml — two ClusterIssuer objects: letsencrypt-staging and "
    "letsencrypt-prod, both using the ACME HTTP-01 solver against ingressClassName: kong, pointed at the "
    "Let's Encrypt staging/production ACME directories respectively. The email field is a REPLACE_ME "
    "placeholder that must be filled in before use; DNS-01 is noted as the alternative for private clusters."
)

doc.add_heading2("2.5 Certificate generation and CI validation")
doc.add_paragraph(
    "scripts/generate-certs.sh — generates nginx/certs/gateway.crt and gateway.key via "
    "`openssl req -x509 -nodes -newkey rsa:2048 -days 365`, SHA-256, CN=localhost, "
    "subjectAltName DNS:localhost,DNS:nginx,IP:127.0.0.1, using an -config file (not -subj) specifically so "
    "the script behaves correctly under Git Bash on Windows. Skips regeneration if a cert/key already exist."
)
doc.add_paragraph(
    ".github/workflows/ci.yaml — six jobs on every push/PR to main: lint-kong-config (`kong config parse` "
    "against kong/kong.yml inside the real kong:3.7 image), validate-compose (`docker compose config "
    "--quiet`), validate-nginx-config (generates certs, then `nginx -t` inside nginx:1.27-alpine), "
    "validate-kubernetes-yaml (kubeconform against everything under kubernetes/ except namespace/CRDs which "
    "have no public schema, explicitly `-skip KongPlugin,KongClusterPlugin,KongConsumer`), "
    "lint-helm-values (`helm template` renders the real kong/kong chart with helm-values.yaml), and "
    "e2e-smoke-test (builds the full Compose stack, waits for all containers healthy, then asserts: "
    "unauthenticated /api/orders succeeds, unauthenticated /api/users returns 401, authenticated /api/users "
    "with the demo key succeeds, and 8 rapid requests to /api/orders produce at least one 429)."
)

# ------------------------------------------------------------------
# 3. Kong declarative configuration structure + route/plugin reference
# ------------------------------------------------------------------
doc.add_heading1("3. Kong declarative configuration structure and route reference")
doc.add_paragraph(
    "In place of a database schema, this section documents the structure of Kong's declarative configuration "
    "(equivalent to a schema for this system) and the concrete route/plugin/backend combinations exposed "
    "through the gateway."
)

doc.add_heading2("3.1 Services | Routes | Plugins | Consumers reference")
doc.add_table(
    headers=["Entity", "Name(s) in kong.yml", "Key fields"],
    rows=[
        ["Service", "users-service, orders-service, reports-service", "url, connect_timeout, read_timeout, "
         "write_timeout (see table in section 2.2)"],
        ["Route", "users-route, orders-route, reports-route", "paths (one prefix each), strip_path: true, "
         "methods: [GET]"],
        ["Route-scoped plugin", "key-auth (users-route only), rate-limiting (all three routes)", "See "
         "section 2.2 for exact config values per route"],
        ["Global plugin", "cors, file-log, correlation-id", "Apply to every route regardless of service; "
         "declared once at the top level of kong.yml"],
        ["Consumer", "demo-consumer", "One keyauth_credentials entry (demo-key-CHANGE-ME-6f3a9c1d)"],
    ],
)

doc.add_heading2("3.2 Sample microservice endpoints exposed through the gateway")
doc.add_table(
    headers=["Public route (via gateway)", "Plugins applied", "Backend service", "Backend endpoint"],
    rows=[
        ["GET /api/users", "key-auth, rate-limiting (20/min), + global cors/file-log/correlation-id",
         "users-service:3001", "GET /"],
        ["GET /api/users/{id}", "key-auth, rate-limiting (20/min), + global plugins", "users-service:3001",
         "GET /:id"],
        ["GET /api/orders", "rate-limiting (5/min), + global plugins", "orders-service:3002", "GET /"],
        ["GET /api/orders/{id}", "rate-limiting (5/min), + global plugins", "orders-service:3002", "GET /:id"],
        ["GET /api/reports", "rate-limiting (10/min), + global plugins", "reports-service:8000", "GET /"],
        ["GET /api/reports/slow", "rate-limiting (10/min), + global plugins; upstream read_timeout 3000ms "
         "causes a 504 before the ~5s handler completes", "reports-service:8000", "GET /slow"],
        ["GET /api/reports/{id}", "rate-limiting (10/min), + global plugins", "reports-service:8000",
         "GET /{report_id}"],
        ["GET /health (each service, not gateway-routed)", "none — not exposed through Kong", "each service "
         "directly (Compose healthcheck only)", "GET /health"],
    ],
)

# ------------------------------------------------------------------
# 4. Sequence flows / process flows
# ------------------------------------------------------------------
doc.add_heading1("4. Sequence flows / process flows")

doc.add_heading2("4.1 TLS handshake, then authenticated proxy to users-service")
doc.add_table(
    headers=["Step", "Actor/Component", "Action"],
    rows=[
        ["1", "Client", "Opens TCP connection to Nginx on host port 8443 and initiates a TLS handshake."],
        ["2", "Nginx", "Terminates TLS using gateway.crt/gateway.key (TLSv1.2/1.3, HIGH:!aNULL:!MD5 "
         "ciphers); on success, decrypts the HTTP request GET /api/users with header apikey: "
         "demo-key-CHANGE-ME-6f3a9c1d."],
        ["3", "Nginx", "Matches location /api/ and proxy_passes to kong_upstream (kong:8000), adding "
         "X-Real-IP, X-Forwarded-For, X-Forwarded-Proto headers."],
        ["4", "Kong", "Matches users-route (path prefix /api/users); runs key-auth plugin, finds a valid "
         "apikey matching demo-consumer's credential, strips the header (hide_credentials: true)."],
        ["5", "Kong", "Runs rate-limiting plugin for users-route; increments the local per-minute counter "
         "(limit 20); request is within limit."],
        ["6", "Kong", "Runs global plugins: cors (adds CORS headers), correlation-id (generates a UUID for "
         "X-Kong-Request-Id), file-log (writes an access log line to stdout)."],
        ["7", "Kong", "strip_path removes /api/users; proxies GET / to http://users-service:3001 with a "
         "2000ms connect timeout / 5000ms read/write timeout."],
        ["8", "users-service", "Sets X-Upstream-Service: users-service and returns the USERS array as JSON."],
        ["9", "Kong", "Adds X-Kong-Upstream-Latency/X-Kong-Proxy-Latency and X-RateLimit-Remaining-Minute "
         "response headers; returns the response to Nginx."],
        ["10", "Nginx / Client", "Nginx relays the response over the established TLS connection to the client."],
    ],
)

doc.add_heading2("4.2 Unauthenticated request rejected by key-auth")
doc.add_table(
    headers=["Step", "Actor/Component", "Action"],
    rows=[
        ["1", "Client", "Sends GET /api/users over HTTPS with no apikey header."],
        ["2", "Nginx", "Terminates TLS, proxies to kong_upstream as in flow 4.1."],
        ["3", "Kong", "Matches users-route; key-auth plugin finds no apikey header (or an invalid one)."],
        ["4", "Kong", "Short-circuits the request — rate-limiting and the upstream service are never "
         "reached; returns HTTP 401 with body {\"message\":\"No API key found in request\"}."],
        ["5", "Nginx / Client", "Relays the 401 response unchanged back to the client."],
    ],
)

doc.add_heading2("4.3 Rate limit exceeded on orders-service")
doc.add_table(
    headers=["Step", "Actor/Component", "Action"],
    rows=[
        ["1", "Client", "Sends 6+ GET /api/orders requests within the same minute."],
        ["2", "Kong (requests 1-5)", "orders-route has no key-auth, so rate-limiting is the only gate; each "
         "of the first 5 requests increments the local per-minute counter and is proxied to "
         "orders-service:3002, returning 200 with decreasing X-RateLimit-Remaining-Minute values."],
        ["3", "Kong (request 6+)", "The local counter for this route has reached its configured minute: 5 "
         "limit; orders-service is never invoked for this request."],
        ["4", "Kong", "Returns HTTP 429 (fault_tolerant: true means Kong still serves this decision even if "
         "its internal counter store had an issue, rather than failing open/closed unpredictably)."],
        ["5", "Nginx / Client", "Relays the 429 back to the client; the counter resets after the minute "
         "window elapses."],
    ],
)

doc.add_heading2("4.4 Upstream timeout on the intentionally slow reports endpoint")
doc.add_table(
    headers=["Step", "Actor/Component", "Action"],
    rows=[
        ["1", "Client", "Sends GET /api/reports/slow."],
        ["2", "Kong", "Matches reports-route; rate-limiting and global plugins pass; proxies to "
         "http://reports-service:8000/slow with read_timeout: 3000ms configured on the reports-service "
         "Kong service."],
        ["3", "reports-service", "Begins `await asyncio.sleep(5)` — will not respond for ~5 seconds."],
        ["4", "Kong", "At 3000ms, its read_timeout for this upstream elapses before reports-service "
         "responds; Kong abandons the wait and returns HTTP 504 to Nginx."],
        ["5", "reports-service", "Independently completes its 5s sleep and returns a 200 body — but this "
         "response is discarded/unused because Kong already responded 504 to the caller."],
        ["6", "Nginx / Client", "Relays the 504 to the client. (README notes: lowering the timeout further, "
         "or shortening the sleep, changes which side of the race wins.)"],
    ],
)

# ------------------------------------------------------------------
# 5. Key algorithms & business logic
# ------------------------------------------------------------------
doc.add_heading1("5. Key algorithms & business logic")

doc.add_heading2("5.1 Rate-limiting algorithm and thresholds")
doc.add_paragraph(
    "Kong's rate-limiting plugin (bundled, not custom) uses a fixed-window counter keyed by client and route, "
    "reset every 60 seconds, configured with policy: local — counters are held in each Kong node's local "
    "memory rather than a shared store (e.g. Redis), which is accurate for this repository's single-Kong-"
    "instance topology but would under- or over-count if multiple Kong replicas were running behind Nginx's "
    "load-balancing upstream block without switching to a shared policy. fault_tolerant: true means the "
    "plugin will not block traffic if its own counter storage encounters an error. hide_client_headers is "
    "explicitly set to false on every route so X-RateLimit-Remaining-Minute (and related headers) are always "
    "returned to the caller, by design, as part of the reference's observability story. Thresholds: "
    "users-service 20/min, orders-service 5/min, reports-service 10/min — orders-service's threshold is "
    "deliberately the tightest so the README's 6-request curl loop reliably demonstrates a 429."
)

doc.add_heading2("5.2 CORS policy specifics")
doc.add_paragraph(
    "A single global cors plugin instance governs every route identically: any origin is allowed "
    "(origins: [\"*\"]), only GET/POST/OPTIONS methods are permitted, only the Accept/Content-Type/apikey "
    "request headers are allowed through, only X-Upstream-Service and X-RateLimit-Remaining-Minute are "
    "exposed to browser JavaScript, credentials: false (no cookies/Authorization forwarding), and preflight "
    "responses are cached for max_age: 3600 seconds. There is no per-route CORS override — every route "
    "inherits this single policy."
)

doc.add_heading2("5.3 Request transformation / path handling")
doc.add_paragraph(
    "The only \"transformation\" logic present is path-stripping: every route sets strip_path: true, so "
    "Kong removes the matched prefix (/api/users, /api/orders, /api/reports) before proxying upstream. This "
    "is why each backend service's own route handlers are written against bare paths (GET /, GET /:id, "
    "GET /slow) with no knowledge of the /api/* prefix — the gateway, not the upstream, owns the public URL "
    "shape. No header rewriting, body transformation, or request/response transformer plugins are configured "
    "anywhere in this repository."
)

doc.add_heading2("5.4 Correlation / tracing logic")
doc.add_paragraph(
    "The correlation-id plugin generates a uuid per request (generator: uuid), attaches it as "
    "X-Kong-Request-Id, and echo_downstream: true ensures the same ID is also returned in the response "
    "headers to the client — allowing a single request to be traced across Nginx's access log, Kong's "
    "file-log output, and the backend service's own log line, using the same identifier throughout."
)

# ------------------------------------------------------------------
# 6. Validation & error handling
# ------------------------------------------------------------------
doc.add_heading1("6. Validation & error handling")
doc.add_table(
    headers=["Scenario", "Handling"],
    rows=[
        ["Missing/invalid API key (users-service route)", "Kong's key-auth plugin returns HTTP 401 with "
         "body {\"message\":\"No API key found in request\"} before the request reaches rate-limiting or "
         "the upstream — verified explicitly in CI's e2e-smoke-test job."],
        ["Rate limit exceeded (any route)", "Kong's rate-limiting plugin returns HTTP 429 once the route's "
         "local per-minute counter is exceeded; X-RateLimit-Remaining-Minute is still returned so the caller "
         "can see it hit 0. Verified in CI by hammering /api/orders 8 times and asserting a 429 appears."],
        ["Backend service failure / unreachable", "Kong's connect_timeout (2000ms for all three services) "
         "governs how long Kong waits to establish a TCP connection to an upstream before failing; if the "
         "upstream never becomes reachable, Kong returns a 502/503-class error. This repository has no "
         "explicit circuit-breaker or retry plugin configured — a known gap if an upstream were flapping."],
        ["Backend service slow / exceeds read_timeout", "Kong's per-service read_timeout (5000ms for users/"
         "orders-service, 3000ms for reports-service) governs how long Kong waits for a response after "
         "connecting; exceeding it returns HTTP 504, independent of any timeout Nginx or the client set — "
         "demonstrated deliberately via reports-service's /slow endpoint."],
        ["Nginx-level upstream failure", "The kong_upstream block marks a Kong server unhealthy after "
         "max_fails=3 within fail_timeout=10s and stops sending it traffic for that window — relevant once "
         "more than one Kong replica is listed; with only one replica configured today, a Kong outage simply "
         "surfaces as Nginx proxy errors to the client."],
        ["Unknown route (not under /api/)", "Nginx's catch-all location / returns a static 404 "
         "{\"error\":\"not found - all routes are served under /api/\"} without ever reaching Kong."],
        ["Unknown resource within a service (e.g. bad :id)", "Each backend service handles this itself: "
         "users-service and orders-service return 404 {\"error\": \"...not found\"} JSON; reports-service's "
         "GET /{report_id} returns a 404 JSONResponse with the same shape."],
        ["Kong Admin API misuse", "No authentication is configured in front of Kong's Admin API in this "
         "demo — it is a known, explicitly documented gap that is mitigated only by network exposure control "
         "(host-only port in Compose, ClusterIP in Kubernetes), not by an auth plugin. Must not be exposed "
         "publicly under any circumstances."],
        ["Nginx config or Kong config errors at deploy time", "Caught before runtime by CI: `nginx -t` "
         "against the real nginx:1.27-alpine image and `kong config parse` against the real kong:3.7 image, "
         "both run on every push/PR."],
    ],
)

# ------------------------------------------------------------------
# 7. Non-functional implementation details
# ------------------------------------------------------------------
doc.add_heading1("7. Non-functional implementation details")

doc.add_heading2("7.1 Security implementation specifics")
doc.add_bullets([
    "TLS: ssl_protocols TLSv1.2 TLSv1.3 only (no TLS 1.0/1.1/SSLv3); ssl_ciphers HIGH:!aNULL:!MD5 with "
    "ssl_prefer_server_ciphers on; ssl_session_cache shared:SSL:10m / ssl_session_timeout 10m for session "
    "resumption performance.",
    "HSTS: Strict-Transport-Security max-age=63072000 (2 years) sent on every response from the 443 server "
    "block, instructing compliant clients to only ever use HTTPS for this host going forward.",
    "Clickjacking/MIME-sniffing hardening: X-Frame-Options: DENY and X-Content-Type-Options: nosniff on "
    "every response.",
    "Body size cap: client_max_body_size 5m at the Nginx edge, before any request reaches Kong or an "
    "upstream.",
    "Container hardening: all three sample services run as non-root (node's built-in node user; "
    "reports-service's appuser, uid 1000); Kubernetes Deployments add runAsNonRoot: true, "
    "allowPrivilegeEscalation: false, capabilities.drop: [\"ALL\"].",
    "Credential hygiene: the only credential in the repository (demo-key-CHANGE-ME-6f3a9c1d) is named to be "
    "obviously a placeholder in any log/report it appears in; real secrets are explicitly kept out of "
    "kong.yml/kong-consumers.yaml by design (both are meant to be replaced, not just have values edited "
    "in place, per the README).",
])

doc.add_heading2("7.2 Performance considerations actually relevant to this repository")
doc.add_bullets([
    "Nginx keepalive 32 on the kong_upstream block reuses connections to Kong rather than reconnecting per "
    "request.",
    "Kong's per-service timeouts are intentionally tight (2s connect across all services; 3s read/write for "
    "reports-service specifically) so that a slow/unresponsive upstream fails fast rather than holding a "
    "Nginx worker connection open indefinitely.",
    "No caching layer (proxy-cache plugin, CDN, etc.) is configured anywhere — every request is proxied "
    "live to the upstream on every call.",
    "No connection pooling/keepalive tuning is configured between Kong and the upstream services beyond "
    "Kong's own defaults — not customized in kong.yml.",
    "The repository explicitly disclaims any measured throughput or latency numbers; the only performance-"
    "relevant behavior that can be observed today is qualitative (e.g. the 504-vs-5s-sleep race on "
    "/api/reports/slow, and the 429 after 5 requests/minute on /api/orders).",
])

# ------------------------------------------------------------------
# 8. Appendix
# ------------------------------------------------------------------
doc.add_heading1("8. Appendix")

doc.add_heading2("8.1 Repository module / file map")
doc.add_code_block(
"""Darviq-Gateway/
  README.md                        Architecture, run instructions, security notes, non-claims
  docker-compose.yml                Full local stack: 3 services + Kong + Nginx
  .env.example                      Non-secret local config (ports, demo API key)
  .gitignore

  services/
    users-service/
      app.js                        Node/Express - GET /, /:id, /health
      package.json, package-lock.json
      Dockerfile                    node:20-alpine, non-root "node" user
    orders-service/
      app.js                        Node/Express - GET /, /:id, /health
      package.json, package-lock.json
      Dockerfile                    node:20-alpine, non-root "node" user
    reports-service/
      app.py                        Python/FastAPI - GET /, /slow, /:id, /health
      requirements.txt
      Dockerfile                    python:3.12-slim, non-root "appuser"

  kong/
    kong.yml                        DB-less declarative config: services, routes,
                                     consumers, plugins (key-auth, rate-limiting,
                                     cors, file-log, correlation-id)

  nginx/
    nginx.conf                      Base config: logging format, includes conf.d/
    conf.d/gateway.conf              TLS termination, HTTP->HTTPS redirect, reverse
                                     proxy + upstream/load-balancing block to Kong
    certs/                          Generated locally, gitignored (.gitkeep only)

  scripts/
    generate-certs.sh                Self-signed cert generator for local dev

  kubernetes/
    namespace.yaml                   gateway-demo namespace
    backend-services/
      users-service.yaml             Deployment + Service
      orders-service.yaml             Deployment + Service
      reports-service.yaml            Deployment + Service
    kong/
      helm-values.yaml                Values for the official kong/kong Helm chart
    ingress/
      ingress.yaml                    Ingress per service
      kong-plugins.yaml               KongPlugin / KongClusterPlugin CRDs
      kong-consumers.yaml             Demo KongConsumer + key-auth credential Secret
    cert-manager/
      cluster-issuer.yaml             Let's Encrypt ClusterIssuer examples

  .github/
    workflows/ci.yaml                 Lint/validate everything + e2e smoke test

  Docs/
    Darviq_Gateway_High_Level_Design.docx
    Darviq_Gateway_Low_Level_Design.docx
    docx_builder.py                   Shared doc-generation helper (kept for regeneration)
    generate_hld.py / generate_lld.py  Generation scripts (kept for regeneration)
"""
)

doc.add_heading2("8.2 Environment variable / configuration reference")
doc.add_table(
    headers=["Name", "Default", "Defined in", "Purpose"],
    rows=[
        ["NGINX_HTTP_HOST_PORT", "8080", ".env.example / docker-compose.yml", "Host port for Nginx's "
         "HTTP (redirect) listener"],
        ["NGINX_HTTPS_HOST_PORT", "8443", ".env.example / docker-compose.yml", "Host port for Nginx's "
         "HTTPS (TLS) listener"],
        ["KONG_ADMIN_HOST_PORT", "8001", ".env.example / docker-compose.yml", "Host port for Kong's "
         "Admin API (local inspection only)"],
        ["DEMO_API_KEY", "demo-key-CHANGE-ME-6f3a9c1d", ".env.example", "Reference copy of the demo "
         "key-auth credential for curl examples; editing this alone does not change what Kong accepts"],
        ["KONG_DATABASE", "off", "docker-compose.yml (kong service env)", "Selects DB-less mode"],
        ["KONG_DECLARATIVE_CONFIG", "/kong/declarative/kong.yml", "docker-compose.yml (kong service env)",
         "In-container path kong.yml is mounted to"],
        ["KONG_PROXY_LISTEN", "0.0.0.0:8000", "docker-compose.yml (kong service env)", "Kong proxy bind "
         "address/port"],
        ["KONG_ADMIN_LISTEN", "0.0.0.0:8001", "docker-compose.yml (kong service env)", "Kong Admin API "
         "bind address/port"],
        ["PORT (users-service)", "3001", "docker-compose.yml / app.js", "Express listen port"],
        ["PORT (orders-service)", "3002", "docker-compose.yml / app.js", "Express listen port"],
    ],
)

doc.add_heading2("8.3 Change history")
doc.add_table(
    headers=["Version", "Date", "Description"],
    rows=[
        ["1.0", "July 31, 2026", "Initial low-level design document"],
    ],
)

doc.save(os.path.join(HERE, "Darviq_Gateway_Low_Level_Design.docx"))
print("Wrote Darviq_Gateway_Low_Level_Design.docx")
