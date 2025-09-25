#!/usr/bin/env bash

set -eu -o pipefail

# Prerequisites:
#   - jq
#   - curl

# Input parameters.
: "${ES_SCHEME:=http}"
: "${ES_SEEDS:=127.0.0.1}"
: "${ES_PORT:=9200}"
: "${ES_USER:=}"
: "${ES_PWD:=}"
: "${ES_VERSION:=v7}"
: "${ES_VIS_INDEX_V1:=temporal_visibility_v1_dev}"
: "${AUTO_CONFIRM:=}"
: "${SLICES_COUNT:=auto}"

es_endpoint="${ES_SCHEME}://${ES_SEEDS}:${ES_PORT}"

	@printf $(COLOR) "Install Elasticsearch schema..."
	curl --fail -X PUT "$es_endpoint/_cluster/settings" -H "Content-Type: application/json" --data-binary @./cluster_settings_v7.json --write-out "\n"
	curl --fail -X PUT "$es_endpoint/_template/temporal_visibility_v1_template" -H "Content-Type: application/json" --data-binary @./index_template_v7.json --write-out "\n"
# No --fail here because create index is not idempotent operation.
	curl -X PUT "$es_endpoint/$ES_VIS_INDEX_V1" --write-out "\n"