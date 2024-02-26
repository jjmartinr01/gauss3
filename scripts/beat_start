#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


exec celery -A gauss.celery_app beat -l INFO