FROM temporalio/server:1.26.3

COPY temporal/config_template.yaml /etc/temporal/config/config_template.yaml
COPY temporal/setup.sh /etc/temporal/setup.sh

ENTRYPOINT ["/etc/temporal/setup.sh"]
