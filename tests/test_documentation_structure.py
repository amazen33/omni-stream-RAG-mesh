from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docs_directory_is_consolidated_to_four_files() -> None:
    docs_docs = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs").rglob("*.md")
    }

    assert docs_docs == {
        "docs/API_AND_CONTRIBUTOR_GUIDE.md",
        "docs/ARCHITECTURE_AND_OPERATIONS.md",
        "docs/c4-model/C4_MODEL.md",
        "docs/TOGAF_Architecture_Definition.md",
    }


def test_togaf_and_c4_documents_preserve_required_project_views() -> None:
    togaf = (ROOT / "docs/TOGAF_Architecture_Definition.md").read_text(encoding="utf-8")
    c4 = (ROOT / "docs/c4-model/C4_MODEL.md").read_text(encoding="utf-8")

    assert "## How to apply ADM in this project" in togaf
    for phase in ("Phase A", "Phase B", "Phase C", "Phase D", "Phase E", "Phase F–H"):
        assert phase in togaf

    for level in ("Level 1", "Level 2", "Level 3", "Level 4"):
        assert level in c4
    assert c4.count("```mermaid") >= 4
    assert "## Applying C4 to project changes" in c4
