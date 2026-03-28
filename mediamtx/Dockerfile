FROM bluenviron/mediamtx:1

# Install bash and jq (used by the startup script to parse options.json)
RUN apk add --no-cache bash jq

# Copy startup script
COPY rootfs/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
