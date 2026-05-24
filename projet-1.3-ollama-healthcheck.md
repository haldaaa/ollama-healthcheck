# Projet 1.3 — Ollama Health Checker

## Objectif pédagogique

Construire un **petit outil Python utile** que tu pourras réellement utiliser plus tard (Phase 2 Docker, Phase 4 IaC, Phase 5 Observability) quand tu auras plusieurs instances Ollama à surveiller.

Contrairement au 1.2 (lecture de code), ici tu écris du code from scratch — mais ça reste petit, sync, sans abstraction. Pas d'async, pas de classes complexes, pas de Pydantic. Juste du Python utilitaire propre.

**Ce que tu apprends en faisant :**
- argparse (CLI Python standard)
- httpx en mode sync (appels HTTP simples)
- PyYAML (parsing de config YAML — tu connais le format, c'est l'approche qui change)
- logging (mise en place + niveaux — vu en lecture en 1.2, ici tu l'utilises pour de vrai)
- dataclasses (introduction douce aux structures typées avant Pydantic)
- gestion d'erreurs sur les appels réseau (timeout, connection refused)
- formatage de sortie (stdout coloré + JSON)

**Ce que tu n'apprends PAS dans ce projet :**
- Pydantic complet (juste un teaser via dataclasses)
- async (gardé pour quand ça sera utile en pratique)
- multi-providers (sortit de la roadmap)

---

## Le résultat final

Un script CLI qui prend un fichier de config YAML listant tes instances Ollama, et qui sort un rapport sur chacune :

```bash
$ ollama-healthcheck --config hosts.yaml

[OK]   local         http://localhost:11434       latency=12ms   models=3   size=4.2GB
[OK]   dev-server    http://192.168.1.100:11434   latency=89ms   models=1   size=2.0GB
[FAIL] docker-stack  http://ollama-docker:11434   error=connection refused
[FAIL] prod-test     http://10.0.0.5:11434        error=timeout (5s)

Summary: 2/4 healthy
```

Et avec `--output json` :
```bash
$ ollama-healthcheck --config hosts.yaml --output json
[
  {"name": "local", "url": "...", "reachable": true, "latency_ms": 12, "models_count": 3, ...},
  {"name": "docker-stack", "url": "...", "reachable": false, "error": "connection refused"},
  ...
]
```

---

## Setup initial

### Étape 1 — Créer le projet

```bash
mkdir -p ~/projets/ollama-healthcheck
cd ~/projets/ollama-healthcheck
python -m venv venv
source venv/bin/activate
git init
```

Crée un `.gitignore` :
```
venv/
__pycache__/
*.pyc
.env
```

Crée un `requirements.txt` (vide pour l'instant, on remplit au fur et à mesure) :
```bash
touch requirements.txt
```

Crée le fichier principal :
```bash
touch ollama_healthcheck.py
```

### Étape 2 — Squelette CLI avec argparse

Premier code, juste pour vérifier que la CLI répond :

```python
# ollama_healthcheck.py
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
```

Test :
```bash
python ollama_healthcheck.py --help
python ollama_healthcheck.py --config test.yaml
python ollama_healthcheck.py --config test.yaml --output json --timeout 10 -v
```

Tu dois voir argparse afficher l'aide et tes args. Si OK, commit.

### Étape 3 — Format de config YAML

Crée `config.example.yaml` :
```yaml
ollamas:
  - name: local
    url: http://localhost:11434
  - name: dev-server
    url: http://192.168.1.100:11434
    timeout: 10                # override le timeout global pour celui-ci
  - name: docker-stack
    url: http://ollama-docker:11434
```

Et un `hosts.yaml` à toi (gitignored) avec tes vrais Ollamas pour tester. Mets ton localhost dedans.

Ajoute `hosts.yaml` au `.gitignore` (config locale, pas committable).

### Étape 4 — Charger le YAML

```bash
pip install pyyaml
pip freeze > requirements.txt
```

Ajoute dans `ollama_healthcheck.py` :

```python
import yaml


def load_config(path: str) -> list[dict]:
    """Charge la config YAML et retourne la liste des Ollamas configurés."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("ollamas", [])
```

Et dans `main()` :
```python
ollamas = load_config(args.config)
print(f"Loaded {len(ollamas)} Ollamas from config")
for ollama in ollamas:
    print(f"  - {ollama['name']}: {ollama['url']}")
```

Test :
```bash
python ollama_healthcheck.py --config hosts.yaml
```

### Étape 5 — Une dataclass pour le résultat

Avant de faire les vrais checks, on définit la structure du résultat. Ajoute en haut du fichier :

```python
from dataclasses import dataclass, field, asdict


@dataclass
class HealthResult:
    name: str
    url: str
    reachable: bool
    latency_ms: float | None = None
    models_count: int | None = None
    models_total_size_mb: float | None = None
    error: str | None = None
```

Une `dataclass` = une classe simple qui te donne automatiquement `__init__`, `__repr__`, etc. C'est le pas avant Pydantic. Tu déclares les champs avec leurs types, Python fait le reste.

Test rapide :
```python
r = HealthResult(name="test", url="http://x:11434", reachable=False, error="timeout")
print(r)
# HealthResult(name='test', url='http://x:11434', reachable=False, latency_ms=None, ...)
print(asdict(r))
# {'name': 'test', 'url': '...', 'reachable': False, ...}
```

### Étape 6 — Le check d'un seul Ollama

Installe httpx :
```bash
pip install httpx
pip freeze > requirements.txt
```

Ajoute la fonction :

```python
import httpx
import time
import logging

logger = logging.getLogger(__name__)


def check_ollama(name: str, url: str, timeout: int = 5) -> HealthResult:
    """Check une instance Ollama et retourne un HealthResult."""
    api_tags_url = f"{url.rstrip('/')}/api/tags"
    logger.debug("Checking %s at %s (timeout=%ds)", name, url, timeout)

    start = time.time()
    try:
        r = httpx.get(api_tags_url, timeout=timeout)
        r.raise_for_status()
        latency_ms = (time.time() - start) * 1000

        data = r.json()
        models = data.get("models", [])
        total_size_bytes = sum(m.get("size", 0) for m in models)
        total_size_mb = total_size_bytes / (1024 * 1024)

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
```

Test isolé en haut de `main()` :
```python
result = check_ollama("local", "http://localhost:11434", timeout=5)
print(result)
```

Tu dois voir un `HealthResult` avec les vraies infos de ton Ollama local. Si ton Ollama ne tourne pas, tu dois voir `reachable=False, error="connection refused"`.

### Étape 7 — Boucle sur tous les Ollamas

Remplace dans `main()` :

```python
results = []
for ollama in ollamas:
    name = ollama["name"]
    url = ollama["url"]
    timeout = ollama.get("timeout", args.timeout)   # override possible
    result = check_ollama(name, url, timeout)
    results.append(result)
```

### Étape 8 — Output text (joli)

Ajoute :

```python
def format_text(results: list[HealthResult]) -> str:
    lines = []
    for r in results:
        if r.reachable:
            lines.append(
                f"[OK]   {r.name:15} {r.url:35} "
                f"latency={r.latency_ms}ms   "
                f"models={r.models_count}   "
                f"size={r.models_total_size_mb}MB"
            )
        else:
            lines.append(f"[FAIL] {r.name:15} {r.url:35} error={r.error}")

    healthy = sum(1 for r in results if r.reachable)
    lines.append(f"\nSummary: {healthy}/{len(results)} healthy")
    return "\n".join(lines)
```

Et dans `main()` :
```python
if args.output == "text":
    print(format_text(results))
```

### Étape 9 — Output JSON

```python
import json


def format_json(results: list[HealthResult]) -> str:
    return json.dumps([asdict(r) for r in results], indent=2)
```

Et :
```python
elif args.output == "json":
    print(format_json(results))
```

### Étape 10 — Logging

En haut de `main()` :

```python
log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

Tu vas voir des logs `DEBUG` quand tu mets `-v`, sinon juste les INFO/WARNING/ERROR.

Ajoute des `logger.info(...)` aux endroits clés (load_config, début/fin du checking, par exemple).

### Étape 11 — README + push

Crée un `README.md` :

```markdown
# Ollama Health Checker

Petit outil CLI pour vérifier l'état de plusieurs instances Ollama.

## Install

\`\`\`bash
git clone https://github.com/haldaaa/ollama-healthcheck
cd ollama-healthcheck
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

## Usage

Crée un fichier de config (cf. \`config.example.yaml\`), puis :

\`\`\`bash
python ollama_healthcheck.py --config hosts.yaml
python ollama_healthcheck.py --config hosts.yaml --output json
python ollama_healthcheck.py --config hosts.yaml -v --timeout 10
\`\`\`

## Format de config

\`\`\`yaml
ollamas:
  - name: local
    url: http://localhost:11434
  - name: dev-server
    url: http://192.168.1.100:11434
    timeout: 10
\`\`\`
```

Crée le repo GitHub `ollama-healthcheck` sur ton compte, push :

```bash
git add .
git commit -m "feat: initial implementation"
git remote add origin git@github.com:haldaaa/ollama-healthcheck.git
git branch -M main
git push -u origin main
```

---

## Critères de réussite

- [ ] La CLI tourne et le `--help` affiche tes options
- [ ] La config YAML est lue correctement
- [ ] Au moins ton Ollama local est checké correctement (status OK)
- [ ] Si tu donnes un host bidon (genre `http://10.99.99.99:11434`), tu vois `[FAIL]` avec une erreur claire (pas un crash)
- [ ] L'output JSON est bien formé (tu peux le piper dans `jq`)
- [ ] Le README est clair, le repo public sur ton GitHub

## Variantes / extensions optionnelles

Si tu veux pousser plus loin (PAS obligatoire) :
- Ajouter `--alert-on-fail` qui exit code 1 si un ou plusieurs Ollamas sont down (utile pour cron + alerting)
- Ajouter `--check-model NAME` qui vérifie aussi qu'un modèle spécifique est présent sur chaque Ollama
- Sortir le format dans Prometheus textfile (préfigure Phase 5)
- Output coloré avec `rich` au lieu de print simple

Note : ces extensions touchent à la frontière Phase 5. Tu peux y revenir plus tard quand tu auras digéré l'observability deep.

## Tips

- Si tu coinces sur un concept Python, retourne au `cours-concepts-python-llm.md`
- Code une étape, teste-la, puis passe à la suivante. Ne code pas tout d'un coup.
- Utilise `print(...)` pour debugger, mais remplace par `logger.debug(...)` à la fin
- Garde les fonctions courtes (<30 lignes). Si une fonction grossit, c'est qu'elle fait trop.

## Pourquoi ce projet est aligné à ton profil

C'est un **vrai outil de monitoring**, pas un exo scolaire. Tu pourras t'en servir en Phase 2 (quand tu containeriseras Ollama et auras besoin de checker), Phase 4 (quand tu auras déployé une stack via Terraform et voudras valider), Phase 5 (quand tu commenceras à instrumenter — tu pourras ajouter Prometheus textfile collector au lieu de stdout). Tu construis ta toolbox personnelle, pas juste tu finis un projet de cours.

Le format CLI + YAML config + dataclasses + httpx sync, c'est aussi le squelette type d'à peu près tous les outils DevOps Python que tu écriras dans ta carrière.
