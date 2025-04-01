#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


exec celery -A gauss.celery worker -c 4 --prefetch-multiplier 4 --max-tasks-per-child 1000 -l INFO --pool=prefork