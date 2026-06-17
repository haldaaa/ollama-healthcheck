# ollama-healthcheck

Health check CLI for Ollama instances. Point it at a YAML config listing your hosts, get a quick status report.

```bash
$ python3 ollama_healthcheck.py --config hosts.yaml

[OK]   local           http://172.24.144.1:11434    latency=54.1ms   models=1   size=1925.8MB

Summary: 1/1 healthy
```

## Install

```bash
git clone https://github.com/haldaaa/ollama-healthcheck
cd ollama-healthcheck
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Config

Create a `hosts.yaml` file (see `config.example.yaml`):

```yaml
ollamas:
  - name: local
    url: http://localhost:11434
  - name: remote
    url: http://192.168.1.100:11434
    timeout: 10
```

## Usage

```bash
# Text output (default)
python3 ollama_healthcheck.py --config hosts.yaml

# JSON output
python3 ollama_healthcheck.py --config hosts.yaml --output json

# Verbose mode (debug logs)
python3 ollama_healthcheck.py --config hosts.yaml -v
```