"""Offline contract tests for the two Inspect Evals Register entry points."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest
from inspect_ai import Task

REPO_ROOT = Path(__file__).resolve().parents[2]
PETRI_ROOT = REPO_ROOT / "petri"
TENET_ID_PATTERN = re.compile(r"^- \*\*(T\d+\.\d+[a-z])\*\*", re.MULTILINE)


def _load_task_module(relative_path: str, module_name: str) -> ModuleType:
    """Load an Inspect task module directly from its source path."""
    task_path = PETRI_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, task_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOUL_DOC_MODULE = _load_task_module(
    "claude_soul_doc_audits/soul_doc_audit.py", "soul_doc_audit"
)
OPENAI_SPEC_MODULE = _load_task_module(
    "openai_model_spec_audits/openai_model_spec_audit.py", "openai_model_spec_audit"
)

soul_doc_audit = SOUL_DOC_MODULE.soul_doc_audit
openai_model_spec_audit = OPENAI_SPEC_MODULE.openai_model_spec_audit
SOUL_DOC_SECTIONS = SOUL_DOC_MODULE.SECTION_MAP
SOUL_DOC_POWER_TENETS = SOUL_DOC_MODULE.POWER_TENETS
OPENAI_SPEC_SECTIONS = OPENAI_SPEC_MODULE.SECTION_MAP


@pytest.mark.parametrize(
    ("factory", "expected_name", "expected_samples"),
    [
        (soul_doc_audit, "soul_doc_audit", 205),
        (openai_model_spec_audit, "openai_model_spec_audit", 197),
    ],
)
def test_register_task_constructs_offline(factory, expected_name, expected_samples):
    """Each register source constructs a complete Inspect Task without API calls."""
    task = factory()

    assert isinstance(task, Task)
    assert task.__registry_info__.name == expected_name
    assert len(task.dataset) == expected_samples
    assert len(task.scorer) > 0
    assert task.solver is not None
    assert task.cleanup is not None

    sample_ids = [sample.id for sample in task.dataset]
    assert all(sample_ids)
    assert len(sample_ids) == len(set(sample_ids))


def test_soul_doc_section_counts_cover_full_dataset():
    expected_counts = {
        "priority": 15,
        "honesty": 27,
        "helpfulness": 31,
        "hierarchy": 13,
        "conflict": 9,
        "hard_constraints": 10,
        "harm": 12,
        "dualuse": 7,
        "safety": 18,
        "epistemic": 8,
        "identity": 12,
        "corrigibility": 7,
        "judgment": 6,
        "formatting": 5,
        "agentic": 5,
        "roleplay": 6,
        "wellbeing": 7,
        "domain": 3,
        "instructable": 4,
    }

    assert {name: len(samples) for name, samples in SOUL_DOC_SECTIONS.items()} == {
        **expected_counts,
        "all": sum(expected_counts.values()),
    }


def test_soul_doc_catalog_distinguishes_paper_and_additional_samples():
    """The paper has 205 samples; the catalog includes six additional power tests."""
    paper_ids = [sample.id for sample in SOUL_DOC_SECTIONS["all"]]
    power_ids = [sample.id for sample in SOUL_DOC_POWER_TENETS]
    catalog = (REPO_ROOT / "tenets/anthropic_constitution.md").read_text(
        encoding="utf-8"
    )
    catalog_ids = TENET_ID_PATTERN.findall(catalog)

    assert len(paper_ids) == len(set(paper_ids)) == 205
    assert len(power_ids) == len(set(power_ids)) == 6
    assert set(paper_ids).isdisjoint(power_ids)
    assert len(catalog_ids) == len(set(catalog_ids)) == 211
    assert set(catalog_ids) == set(paper_ids) | set(power_ids)


def test_openai_spec_section_counts_cover_full_dataset():
    expected_counts = {
        "redline": 17,
        "chain_of_command": 29,
        "content": 23,
        "safety": 23,
        "truth": 44,
        "best_work": 20,
        "style": 32,
        "under18": 9,
    }

    assert {name: len(samples) for name, samples in OPENAI_SPEC_SECTIONS.items()} == {
        **expected_counts,
        "all": sum(expected_counts.values()),
    }


@pytest.mark.parametrize(
    ("factory", "kwargs"),
    [
        (soul_doc_audit, {"section": "not-a-section"}),
        (openai_model_spec_audit, {"spec_section": "not-a-section"}),
    ],
)
def test_register_task_rejects_unknown_sections(factory, kwargs):
    with pytest.raises(ValueError, match="Unknown section"):
        factory(**kwargs)
