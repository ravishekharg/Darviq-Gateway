'use strict';

// users-service
//
// Deliberately minimal. This is a routing target for the Kong/Nginx gateway
// demo, not the point of the project - it exists to prove that requests
// actually traverse Nginx -> Kong -> a real upstream and come back with
// that upstream's identity intact (via the X-Upstream-Service header and
// the "service" field in the JSON body).

const express = require('express');

const app = express();
const PORT = process.env.PORT || 3001;
const SERVICE_NAME = 'users-service';

const USERS = [
  { id: 1, name: 'Asha Rao', role: 'admin' },
  { id: 2, name: 'Priya Nair', role: 'viewer' },
  { id: 3, name: 'Marcus Chen', role: 'editor' },
];

app.use((req, res, next) => {
  res.setHeader('X-Upstream-Service', SERVICE_NAME);
  next();
});

// Unauthenticated health check - used by the Docker Compose healthcheck and
// is intentionally NOT routed through Kong's key-auth plugin.
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: SERVICE_NAME });
});

// Kong's route for this service (kong/kong.yml -> users-route) has
// strip_path: true and matches /api/users, so a client request to
// /api/users arrives here as GET / - this service knows nothing about
// the /api prefix, which is deliberate: the gateway owns the public URL
// shape, not the upstream.
app.get('/', (req, res) => {
  res.json({
    service: SERVICE_NAME,
    upstream: `${SERVICE_NAME}:${PORT}`,
    receivedPath: req.originalUrl,
    count: USERS.length,
    users: USERS,
  });
});

app.get('/:id', (req, res) => {
  const user = USERS.find((u) => u.id === Number(req.params.id));
  if (!user) {
    return res.status(404).json({ service: SERVICE_NAME, error: 'user not found' });
  }
  return res.json({ service: SERVICE_NAME, user });
});

app.use((req, res) => {
  res.status(404).json({ service: SERVICE_NAME, error: 'not found', path: req.originalUrl });
});

app.listen(PORT, () => {
  console.log(`[${SERVICE_NAME}] listening on port ${PORT}`);
});
