# ollama-healthcheck

CLI tool to check the health of your Ollama instances.

## Install

```bash
git clone https://github.com/haldaaa/ollama-healthcheck
cd ollama-healthcheck
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

Create a config file (see `config.example.yaml`), then:

```bash
python3 ollama_healthcheck.py --config hosts.yaml
python3 ollama_healthcheck.py --config hosts.yaml --output json
python3 ollama_healthcheck.py --config hosts.yaml -v --timeout 10
```