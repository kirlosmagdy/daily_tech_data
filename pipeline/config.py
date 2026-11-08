from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.yaml"


# Load and return the central project configuration dictionary.
def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    cfg = load_config()
    enabled = [k for k, v in cfg["sources"].items() if v.get("enabled")]
    print(f"Loaded '{cfg['project']['name']}' v{cfg['project']['version']} — Enabled sources: {enabled}")