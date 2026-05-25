import argparse
import yaml
from dataclasses import dataclass, asdict


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



def load_config(path: str) -> list[dict]:
    """ Charge la config YAML et retourne la liste des Ollamas configurés """
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("ollamas", [])


if __name__ == "__main__":
    main()