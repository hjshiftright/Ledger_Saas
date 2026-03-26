# ── Ledger — Web Server ───────────────────────────────────────────────────────
# Stage 1: Build the React application with Vite
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first so this layer is cached unless package.json changes
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# Copy source and build
COPY . .

# VITE_API_BASE_URL is intentionally left empty so all /api/ calls are relative.
# Nginx (Stage 2) proxies those relative calls to the API container.
# Override this build arg if you want to point directly at a different API host.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build


# ── Stage 2: Serve with Nginx ─────────────────────────────────────────────────
FROM nginx:1.25-alpine

# Copy built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Replace default Nginx config with our SPA + proxy config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
