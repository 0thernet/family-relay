# Pin the Xray engine by version and immutable image digest.
FROM teddysun/xray:26.3.27@sha256:8c92e146e30e8b3b757a8598054c3a747b72fa2cc47f47d8d7983fe264688b95

USER root
RUN apk add --no-cache python3 \
    && addgroup -S -g 10001 relay \
    && adduser -S -D -H -u 10001 -G relay relay \
    && mkdir -p /opt/relay \
    && chmod 0755 /opt /opt/relay
COPY --chmod=0644 docker/entrypoint.py /opt/relay/entrypoint.py
USER 10001:10001
EXPOSE 443 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python3", "/opt/relay/entrypoint.py", "--health"]
ENTRYPOINT ["python3", "/opt/relay/entrypoint.py"]
