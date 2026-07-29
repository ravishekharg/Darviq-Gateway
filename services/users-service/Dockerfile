# users-service - minimal Node/Express routing target
FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY app.js ./

# Runs as the non-root "node" user baked into the official image.
USER node

EXPOSE 3001

CMD ["node", "app.js"]
