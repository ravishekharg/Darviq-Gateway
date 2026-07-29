'use strict';

// orders-service
//
// Second routing target for the gateway demo. Kept as small as
// users-service on purpose - the interesting engineering in this repo is
// in kong/kong.yml, nginx/, and docker-compose.yml, not here.

const express = require('express');

const app = express();
const PORT = process.env.PORT || 3002;
const SERVICE_NAME = 'orders-service';

const ORDERS = [
  { id: 101, item: 'Wireless Mouse', qty: 2, status: 'shipped' },
  { id: 102, item: 'Mechanical Keyboard', qty: 1, status: 'processing' },
  { id: 103, item: 'USB-C Hub', qty: 3, status: 'delivered' },
];

app.use((req, res, next) => {
  res.setHeader('X-Upstream-Service', SERVICE_NAME);
  next();
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: SERVICE_NAME });
});

// Kong's route for this service (kong/kong.yml -> orders-route) has
// strip_path: true and matches /api/orders, so a client request to
// /api/orders arrives here as GET / - see the matching comment in
// users-service/app.js for why.
app.get('/', (req, res) => {
  res.json({
    service: SERVICE_NAME,
    upstream: `${SERVICE_NAME}:${PORT}`,
    receivedPath: req.originalUrl,
    count: ORDERS.length,
    orders: ORDERS,
  });
});

app.get('/:id', (req, res) => {
  const order = ORDERS.find((o) => o.id === Number(req.params.id));
  if (!order) {
    return res.status(404).json({ service: SERVICE_NAME, error: 'order not found' });
  }
  return res.json({ service: SERVICE_NAME, order });
});

app.use((req, res) => {
  res.status(404).json({ service: SERVICE_NAME, error: 'not found', path: req.originalUrl });
});

app.listen(PORT, () => {
  console.log(`[${SERVICE_NAME}] listening on port ${PORT}`);
});
