# Crucible web app: upload a git repo, pick base + PR, run the proof gates on IBM Bob's findings.
FROM python:3.12-slim

# git is needed for worktrees and diffs of the uploaded repository
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && git config --system --add safe.directory '*'

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

# Hosted mode: bind to all interfaces on the platform's $PORT, no server-path loading
ENV CRUCIBLE_HOSTED=1 HOST=0.0.0.0 PORT=8765 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "-m", "crucible.cli", "serve"]
