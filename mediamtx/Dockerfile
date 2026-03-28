ARG BUILD_FROM

# ── Stage 1: grab the mediamtx binary ────────────────────────────────────────
FROM bluenviron/mediamtx:1 AS mediamtx-source

# ── Stage 2: HA base image with bashio / S6 overlay ──────────────────────────
FROM ${BUILD_FROM}

# Copy the statically-compiled mediamtx binary from the upstream image
COPY --from=mediamtx-source /mediamtx /usr/bin/mediamtx

# Copy add-on filesystem overlay (S6 services, scripts)
COPY rootfs /

RUN chmod a+x \
      /etc/services.d/mediamtx/run \
      /etc/services.d/mediamtx/finish
