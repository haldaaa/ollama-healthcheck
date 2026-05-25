"""
ollama_healthcheck.py — CLI tool to check the health of one or more Ollama instances.
Reads a YAML config file and reports reachability, latency, and loaded models.
25/05/2026 GASMI Fares
"""

import argparse
import yaml
from dataclasses import dataclass, asdict


# Holds the result of a single Ollama health check
@dataclass
class HealthResult:
    name: str
    url: str
    reachable: bool
    latency_ms: float | None = None
    models_count: int | None = None
    models_total_size_mb: float | None = None
    error: str | None = None



def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(
        description="Health check pour des instances Ollama.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Chemin vers le fichier YAML de config (liste des Ollamas)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Format de sortie",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Timeout par check, en secondes (default: 5)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Active les logs DEBUG",
    )

    args = parser.parse_args()
    ollamas = load_config(args.config)

    print(f"Loaded {len(ollamas)} Ollamas from config")
    for ollama in ollamas:
        print(f"  - {ollama['name']}: {ollama['url']}")



# Load target hosts from config file
def load_config(path: str) -> list[dict]:
    """ Charge la config YAML et retourne la liste des Ollamas configurés """
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("ollamas", [])


if __name__ == "__main__":
    main()