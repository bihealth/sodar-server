#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset


celery -A omics_data_mgmt.taskapp beat -l INFO
