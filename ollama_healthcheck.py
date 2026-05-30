"""
ollama_healthcheck.py — CLI tool to check the health of one or more Ollama instances.
Reads a YAML config file and reports reachability, latency, and loaded models.
25/05/2026 GASMI Fares
"""

import argparse
import time
import httpx
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

    results = []
    for ollama in ollamas:
        result = check_ollama(
            name=ollama["name"],
            url=ollama["url"],
            timeout=ollama.get("timeout", args.timeout),
        )
        results.append(result)
        print(result)



# Load target hosts from config file
def load_config(path: str) -> list[dict]:
    """ Charge la config YAML et retourne la liste des Ollamas configurés """
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("ollamas", [])


def check_ollama(name: str, url: str, timeout: int = 5) -> HealthResult:
    """Check a single Ollama instance and return a HealthResult."""
    api_url = f"{url.rstrip('/')}/api/tags"

    start = time.time()
    try:
        r = httpx.get(api_url, timeout=timeout)
        r.raise_for_status()
        latency_ms = (time.time() - start) * 1000

        models = r.json().get("models", [])
        total_size_mb = sum(m.get("size", 0) for m in models) / (1024 * 1024)

        return HealthResult(
            name=name,
            url=url,
            reachable=True,
            latency_ms=round(latency_ms, 1),
            models_count=len(models),
            models_total_size_mb=round(total_size_mb, 1),
        )
    except httpx.TimeoutException:
        return HealthResult(name=name, url=url, reachable=False, error=f"timeout ({timeout}s)")
    except httpx.ConnectError:
        return HealthResult(name=name, url=url, reachable=False, error="connection refused")
    except httpx.HTTPStatusError as e:
        return HealthResult(name=name, url=url, reachable=False, error=f"HTTP {e.response.status_code}")
    except Exception as e:
        return HealthResult(name=name, url=url, reachable=False, error=str(e))

if __name__ == "__main__":
    main()