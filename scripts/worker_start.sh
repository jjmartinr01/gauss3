#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


exec celery -A gauss.celery worker -l INFO --pool=solo