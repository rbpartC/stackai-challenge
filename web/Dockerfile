FROM temporalio/ui:2.40.1

EXPOSE $TEMPORAL_UI_PORT

ENTRYPOINT ["/bin/sh", "-c", "TEMPORAL_ADDRESS=$TEMPORAL_GRPC_HOST:7233 && ./start-ui-server.sh"]
