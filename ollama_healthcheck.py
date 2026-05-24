import argparse


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
    print(f"Config: {args.config}, Output: {args.output}, Timeout: {args.timeout}s")


if __name__ == "__main__":
    main()