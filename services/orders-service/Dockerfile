# orders-service - minimal Node/Express routing target
FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY app.js ./

USER node

EXPOSE 3002

CMD ["node", "app.js"]
