FROM temporalio/admin-tools:1.28

COPY temporal/config_template.yaml /etc/temporal/config/config_template.yaml
COPY temporal/setup/setup.sh /etc/temporal/setup.sh

ENTRYPOINT ["/etc/temporal/setup.sh"]