"""Registry sanity checks — ensure every package referenced in the registry
has a matching .rego file on disk."""

from __future__ import annotations

from pathlib import Path

from rules_svc.registry import REGISTRY

RULES_ROOT = Path(__file__).resolve().parents[3] / "rules"


def test_registry_packages_have_rego_files():
    missing: list[str] = []
    for spec in REGISTRY.values():
        # package "wfi.comp" -> rules/wfi/comp.rego
        path = RULES_ROOT / spec.package.replace(".", "/")
        candidate = path.with_suffix(".rego")
        if not candidate.exists():
            missing.append(f"{spec.name}: expected {candidate}")
    assert not missing, "missing .rego files for:\n" + "\n".join(missing)


def test_registry_names_match_keys():
    for key, spec in REGISTRY.items():
        assert key == spec.name


def test_every_rego_has_a_registry_entry():
    rego_files = [p for p in (RULES_ROOT / "wfi").rglob("*.rego")]
    registered_packages = {spec.package for spec in REGISTRY.values()}
    missing: list[str] = []
    for path in rego_files:
        # rules/wfi/comp.rego -> wfi.comp
        rel = path.relative_to(RULES_ROOT).with_suffix("")
        package = ".".join(rel.parts)
        if package not in registered_packages:
            missing.append(package)
    assert not missing, f"unregistered rego packages: {missing}"
