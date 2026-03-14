# ===========================================================================
# Hugging Face Spaces – Docker SDK
# Multi-stage build: (1) build ifc-lite viewer, (2) Python runtime with nginx
# ===========================================================================

# --- Stage 1: Build the ifc-lite 3D viewer ---------------------------------
FROM node:20-slim AS viewer-build

WORKDIR /build
COPY Dashboard/ifc-lite/package.json Dashboard/ifc-lite/package-lock.json ./
RUN npm ci --ignore-scripts
COPY Dashboard/ifc-lite/ ./
RUN npm run build

# --- Stage 2: Python runtime -----------------------------------------------
FROM python:3.11-slim

# nginx for reverse-proxying Streamlit + viewer + static files on one port
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces convention: non-root user with uid 1000
RUN useradd -m -u 1000 user

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (Dashboard + core only – no Training / Evaluation)
COPY core/                       core/
COPY Dashboard/                  Dashboard/
COPY Ökobilanzdaten.sqlite3      ./

# Pre-built ifc-lite viewer (from stage 1)
COPY --from=viewer-build /build/dist/ Dashboard/ifc-lite/dist/

# nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Streamlit configuration
RUN mkdir -p /app/.streamlit
COPY .streamlit/config.toml /app/.streamlit/config.toml

# Startup helper
COPY start.sh .
RUN chmod +x start.sh

# Writable directories for runtime data
RUN mkdir -p /app/Dashboard/static /app/Dashboard/data /app/models \
    && chown -R user:user /app /var/log/nginx /var/lib/nginx /run

EXPOSE 7860

USER user

CMD ["./start.sh"]
