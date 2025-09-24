FROM temporalio/auto-setup:1.14.3

# Docker context is set to the root of this repo
COPY config/dynamicconfig.yaml /etc/temporal/dynamicconfig.yaml
COPY config/dynamicconfig_es.yaml /etc/temporal/dynamicconfig_es.yaml
COPY config/config_template.yaml /etc/temporal/config/config_template.yaml
COPY server/auto-setup/auto-setup-override.sh /etc/temporal/auto-setup.sh
COPY server/.bashrc /home/temporal/.bashrc