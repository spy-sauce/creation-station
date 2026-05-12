# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Talent Agent — Frontend Dockerfile                                        ║
# ║  VibeSpace LLC · Multi-stage build: Node → Nginx                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── Stage 1: Build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: Serve with Nginx ────────────────────────────────────────────────
FROM nginx:1.25-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Custom nginx config for SPA routing + API proxy
COPY nginx.conf /etc/nginx/conf.d/talent-agent.conf

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
