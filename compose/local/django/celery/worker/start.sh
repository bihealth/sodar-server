#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace


celery -A omics_data_mgmt.taskapp worker -l INFO
