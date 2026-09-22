from __future__ import annotations

"""
NAME
    test_pipeline.py - Narrow tests for the initial docs-maintenance pipeline.
"""

import tempfile
import unittest
from pathlib import Path

from tools.docs_maintenance.artifacts import write_docs_maintenance_artifacts
from tools.docs_maintenance.inventory import (
    CATEGORY_DOCS,
    CATEGORY_ROOT,
    EDIT_MODE_EDITABLE,
    EDIT_MODE_GENERATED,
    inventory_markdown_documents,
)
from tools.docs_maintenance.pipeline import run_docs_inventory_pipeline


DOC_STATUS_SURFACE_TEXT = "> AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration.\n"
DOC_README_TEXT = "# README\n"
DOC_FEATURE_TEXT = "# Feature\n"
QUALITY_CONCERN_BROKEN_LINKS = "Broken internal links remain unresolved."
ISOLATED_DOCUMENTS_REPO_PATH = "docs/ISOLATED_DOCUMENTS.md"
ISOLATED_FIXTURE_REPO_PATH = "docs/LONELY.md"
ISOLATED_NOT_OBSOLETE_TEXT = "does not mean that a document is obsolete"


class DocsMaintenancePipelineTests(unittest.TestCase):
    def test_inventory_classifies_generated_and_entrypoint_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "STATUS_SURFACE_INVENTORY.md").write_text(
                DOC_STATUS_SURFACE_TEXT,
                encoding="utf-8",
            )
            (root / "docs" / "FEATURE.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")

            documents = inventory_markdown_documents(root)
            by_path = {document.repo_path: document for document in documents}

            self.assertEqual(CATEGORY_ROOT, by_path["README.md"].category)
            self.assertTrue(by_path["README.md"].is_entrypoint)
            self.assertEqual(EDIT_MODE_EDITABLE, by_path["README.md"].edit_mode)
            self.assertEqual(CATEGORY_DOCS, by_path["docs/STATUS_SURFACE_INVENTORY.md"].category)
            self.assertEqual(
                EDIT_MODE_GENERATED,
                by_path["docs/STATUS_SURFACE_INVENTORY.md"].edit_mode,
            )
            self.assertEqual(
                EDIT_MODE_EDITABLE,
                by_path["docs/FEATURE.md"].edit_mode,
            )

    def test_pipeline_report_includes_generated_files_and_orphan_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "docs" / "STATUS_SURFACE_INVENTORY.md").write_text(
                DOC_STATUS_SURFACE_TEXT,
                encoding="utf-8",
            )
            (root / "docs" / "FEATURE.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")

            report = run_docs_inventory_pipeline(root)

            self.assertEqual(4, report["totalPages"])
            self.assertEqual(3, report["editablePages"])
            self.assertEqual(1, report["generatedPages"])
            self.assertIn("docs/STATUS_SURFACE_INVENTORY.md", report["generatedFiles"])
            self.assertIn("README.md", report["entrypoints"])
            self.assertIn("docs/README.md", report["entrypoints"])
            self.assertIn("docs/FEATURE.md", report["orphanCandidates"])

    def test_pipeline_report_tracks_internal_links_and_broken_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("[Docs](docs/README.md)\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text(
                "[Feature](FEATURE.md)\n[Missing](MISSING.md)\n",
                encoding="utf-8",
            )
            (root / "docs" / "FEATURE.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")

            report = run_docs_inventory_pipeline(root)

            self.assertIn("docs/README.md", report["linkedPages"])
            self.assertIn("docs/FEATURE.md", report["linkedPages"])
            self.assertIn(
                {"source": "docs/README.md", "target": "docs/MISSING.md"},
                report["brokenLinks"],
            )
            self.assertNotIn("docs/FEATURE.md", report["orphanCandidates"])

    def test_inventory_excludes_recovery_history_local_ai_and_root_scratch_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "Untitled.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            (root / "report.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            (root / "evolving development.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            recovery = root / "notes" / "recovery" / "snapshot"
            recovery.mkdir(parents=True)
            (recovery / "COPY.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            historical = root / "docs" / "historical"
            historical.mkdir(parents=True)
            (historical / "OLD.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            local_ai = root / ".local-ai" / "regression-reports"
            local_ai.mkdir(parents=True)
            (local_ai / "report.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")

            documents = inventory_markdown_documents(root)
            paths = {document.repo_path for document in documents}

            self.assertEqual({"README.md"}, paths)

    def test_existing_encoded_and_excluded_markdown_targets_are_not_broken(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Current UI Rules.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            skill = root / ".codex" / "skills" / "sample" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text(
                "[Rules](../Current%20UI%20Rules.md)\n"
                "[Skill](../.codex/skills/sample/SKILL.md)\n",
                encoding="utf-8",
            )

            report = run_docs_inventory_pipeline(root)

            self.assertEqual([], report["brokenLinks"])
            self.assertNotIn(
                QUALITY_CONCERN_BROKEN_LINKS,
                report["healthSummary"]["documentationQualityConcerns"],
            )

    def test_pipeline_report_tracks_terminology_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "A.md").write_text(
                "This page uses controlled lifecycle and active-group wording.\n",
                encoding="utf-8",
            )
            (root / "docs" / "B.md").write_text(
                "This page uses scope membership and Active Group wording.\n",
                encoding="utf-8",
            )

            report = run_docs_inventory_pipeline(root)

            scope_membership_entry = next(
                entry
                for entry in report["terminologyVariants"]
                if entry["preferred"] == "scope membership"
            )
            self.assertIn("controlled lifecycle", scope_membership_entry["variants"])
            self.assertIn("scope membership", scope_membership_entry["variants"])
            active_group_entry = next(
                entry
                for entry in report["terminologyVariants"]
                if entry["preferred"] == "Active Group"
            )
            self.assertIn("active-group", active_group_entry["variants"])
            self.assertIn("Active Group", active_group_entry["variants"])

    def test_pipeline_report_tracks_duplicate_title_families(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "FEATURE_SPEC_ALPHA.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            (root / "docs" / "SPEC_ALPHA.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")
            (root / "docs" / "TEST_PLAN_BETA.md").write_text(DOC_FEATURE_TEXT, encoding="utf-8")

            report = run_docs_inventory_pipeline(root)

            self.assertIn(
                {
                    "normalizedTitle": "alpha",
                    "pages": [
                        "docs/FEATURE_SPEC_ALPHA.md",
                        "docs/SPEC_ALPHA.md",
                    ],
                },
                report["duplicateTitles"],
            )

    def test_pipeline_report_proposes_mocs_and_top_level_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(DOC_README_TEXT, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "FEATURE_SPEC_CAN_EVIDENCE_UI.md").write_text(
                "CAN evidence and diagnostics UI.\n",
                encoding="utf-8",
            )
            (root / "docs" / "FEATURE_SPEC_TEST_CREATION_DSL_V1.md").write_text(
                "DSL authoring and runtime.\n",
                encoding="utf-8",
            )
            (root / "docs" / "FEATURE_SPEC_TOPOLOGY_UPGRADE.md").write_text(
                "Topology editor and group routing.\n",
                encoding="utf-8",
            )

            report = run_docs_inventory_pipeline(root)

            moc_titles = {entry["title"] for entry in report["proposedMocs"]}
            self.assertIn("CAN Diagnostics", moc_titles)
            self.assertIn("DSL", moc_titles)
            self.assertIn("Topology", moc_titles)
            diagnostics_entry = next(
                entry for entry in report["topLevelIndex"] if entry["section"] == "Diagnostics"
            )
            self.assertIn("CAN Diagnostics", diagnostics_entry["pages"])
            dsl_entry = next(
                entry for entry in report["topLevelIndex"] if entry["section"] == "DSL"
            )
            self.assertIn("DSL", dsl_entry["pages"])

    def test_pipeline_report_includes_related_topics_glossary_and_renames(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "FEATURE_SPEC_ACTIVE_GROUP.md").write_text(
                "# Active Group\n"
                + ("This page explains active-group behavior and scope membership in operator workflows. " * 6)
                + "\n",
                encoding="utf-8",
            )
            (root / "docs" / "FEATURE_SPEC_SCOPE_MEMBERSHIP.md").write_text(
                "# Scope Membership\n"
                + ("This page explains scope membership and active group behavior across runtime surfaces. " * 6)
                + "\n",
                encoding="utf-8",
            )

            report = run_docs_inventory_pipeline(root)

            self.assertTrue(report["relatedTopicSuggestions"])
            self.assertTrue(report["glossaryEntries"])
            self.assertIn("renameRecommendations", report)
            self.assertIn("healthSummary", report)

    def test_artifact_writer_materializes_index_glossary_and_mocs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "FEATURE_SPEC_TEST_CREATION_DSL_V1.md").write_text(
                "# DSL Authoring\nDSL authoring and runtime.\n",
                encoding="utf-8",
            )
            (root / ISOLATED_FIXTURE_REPO_PATH).write_text(
                "# Lonely\n",
                encoding="utf-8",
            )
            report = run_docs_inventory_pipeline(root)

            written = write_docs_maintenance_artifacts(root, report)

            self.assertIn("docs/INDEX.md", written)
            self.assertIn("docs/GLOSSARY.md", written)
            self.assertIn(ISOLATED_DOCUMENTS_REPO_PATH, written)
            self.assertTrue(any(path.startswith("docs/mocs/") for path in written))
            self.assertTrue((root / "docs" / "INDEX.md").exists())
            self.assertTrue((root / "docs" / "GLOSSARY.md").exists())
            isolated_text = (root / ISOLATED_DOCUMENTS_REPO_PATH).read_text(
                encoding="utf-8"
            )
            self.assertIn(ISOLATED_FIXTURE_REPO_PATH, isolated_text)
            self.assertIn(ISOLATED_NOT_OBSOLETE_TEXT, isolated_text)
            refreshed_report = run_docs_inventory_pipeline(root)
            self.assertIn(
                ISOLATED_FIXTURE_REPO_PATH,
                refreshed_report["orphanCandidates"],
            )


if __name__ == "__main__":
    unittest.main()
