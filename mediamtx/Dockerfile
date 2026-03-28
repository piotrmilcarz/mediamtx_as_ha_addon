# Pull the statically-compiled mediamtx binary from the upstream image
FROM bluenviron/mediamtx:1 AS mediamtx-source

# Use plain Alpine as runtime — no ghcr.io, has apk and a real shell
FROM alpine:3.19

# Install bash and jq for the startup script
RUN apk add --no-cache bash jq

# Copy the static mediamtx binary
COPY --from=mediamtx-source /mediamtx /mediamtx

# Copy startup script
COPY rootfs/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
