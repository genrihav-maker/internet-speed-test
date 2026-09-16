#!/usr/bin/env bash
# Синхронизирует uv.lock с новой версией из pyproject.toml и подкладывает
# его в коммит бампа (вызывается bumpver как pre_commit_hook).
set -euo pipefail

uv lock
git add uv.lock