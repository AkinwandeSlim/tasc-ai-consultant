# =============================================================================
# TASC Frontend — Dockerfile
# Build: docker build -f docker/frontend/Dockerfile -t tasc-frontend .
# =============================================================================

FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies
COPY apps/frontend/package.json apps/frontend/package-lock.json* ./
RUN npm ci

# Copy source and build
COPY apps/frontend/ .
RUN npm run build

# =============================================================================
FROM node:22-alpine AS runtime

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S tasc && \
    adduser -S -u 1001 -G tasc tasc

# Copy built assets from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER tasc

EXPOSE 3000

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

CMD ["node", "server.js"]
