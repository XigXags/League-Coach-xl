"""Configure provider profiles locally without accepting or printing secret tokens."""
import argparse
import copy
import json
import os
from pathlib import Path
import tempfile
from model_profiles import Profiles, ROOT, PROVIDERS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", nargs="?")
    parser.add_argument("--provider", choices=sorted(PROVIDERS - {"builtin"}))
    parser.add_argument("--model")
    parser.add_argument("--key-env", help="Name of environment variable holding the key, never the key itself")
    parser.add_argument("--base-url")
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    registry = Profiles()
    data = copy.deepcopy(registry.data)
    if args.profile:
        if args.enable and args.disable:
            parser.error("Choose enable or disable")
        if args.profile == "legacy":
            parser.error("Keep the legacy rollback profile intact")
        profile = data["profiles"].setdefault(args.profile, {
            "provider": args.provider or "chat_completions", "enabled": False, "model": None,
            "model_env": None, "api_key_env": None, "base_url": None,
            "max_output_tokens": 256, "timeout_seconds": 5, "fallback_profile": "legacy"})
        if args.provider:
            profile["provider"] = args.provider
        if args.model:
            profile["model"], profile["model_env"] = args.model, None
        if args.key_env:
            profile["api_key_env"] = args.key_env
        if args.base_url:
            profile["base_url"] = args.base_url
        if args.enable or args.disable:
            profile["enabled"] = args.enable
    # Validate before replacing a usable config. Temporary validation is isolated.
    with tempfile.TemporaryDirectory() as folder:
        temporary_root = Path(folder)
        (temporary_root / "coach_models.json").write_text(json.dumps(data), encoding="utf-8")
        checked = Profiles(temporary_root)
        if args.profile and args.enable and checked.readiness(args.profile) != "ready":
            parser.error(f"Cannot enable {args.profile}: {checked.readiness(args.profile)}")
    target = ROOT / "coach_models.json"
    pending = target.with_suffix(".tmp")
    pending.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(pending, target)
    print("Configuration saved. In Discord run /model reload:true, then /models.")
    if args.profile:
        print("Profile:", args.profile, "—", checked.readiness(args.profile))


if __name__ == "__main__":
    main()
