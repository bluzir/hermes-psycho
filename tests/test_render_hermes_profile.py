import importlib.util
import pathlib
import copy
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RENDERER_PATH = REPO_ROOT / "scripts" / "render-hermes-profile.py"
MANIFEST_PATH = REPO_ROOT / "hermes-profile.yaml"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_hermes_profile", RENDERER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HermesProfileRendererTests(unittest.TestCase):
    def test_manifest_loads_with_safe_capability_defaults(self):
        renderer = load_renderer()
        manifest = renderer.load_manifest(MANIFEST_PATH)

        self.assertEqual(manifest["profile"]["name"], "relationship")
        self.assertEqual(manifest["owner"]["id"], "you")
        self.assertEqual(manifest["owner"]["shared_root"], "/opt/data/owners/you/shared")
        self.assertEqual(
            manifest["profile"]["canonical_home"],
            "/opt/data/owners/you/profiles/relationship",
        )
        self.assertEqual(manifest["profile"]["timezone"], "UTC")
        self.assertEqual(
            manifest["profile"]["compatibility_home"],
            "/opt/data/profiles/relationship",
        )
        self.assertEqual(manifest["profile"]["hermes_home"], manifest["profile"]["compatibility_home"])
        self.assertEqual(manifest["runtime"]["browser"]["mode"], "disabled")
        self.assertEqual(manifest["runtime"]["swarm"]["enabled"], False)
        self.assertEqual(manifest["knowledge"]["synthesis"]["corpus"], "public_only")
        self.assertEqual(manifest["knowledge"]["synthesis"]["think_enabled"], False)
        self.assertEqual(manifest["knowledge"]["synthesis"]["dream_enabled"], False)
        self.assertEqual(manifest["knowledge"]["synthesis"]["eval_enabled"], False)

    def test_private_dirs_are_not_public_index_dirs(self):
        renderer = load_renderer()
        manifest = renderer.load_manifest(MANIFEST_PATH)

        public_dirs = set(manifest["knowledge"]["public_index_dirs"])
        private_dirs = set(manifest["knowledge"]["private_dirs"])
        self.assertFalse(public_dirs & private_dirs)

    def test_renderer_produces_all_phase_one_artifacts(self):
        renderer = load_renderer()
        manifest = renderer.load_manifest(MANIFEST_PATH)
        rendered = renderer.render_all(manifest)

        self.assertEqual(
            set(rendered),
            {
                "hermes/SOUL.md",
                "deploy/relationship/config.yaml.example",
                "scripts/brain-maintain.sh",
                "scripts/install-gbrain.sh",
                "scripts/gbrain-config.sh",
            },
        )

        for path, content in rendered.items():
            with self.subTest(path=path):
                self.assertIn("generated from hermes-profile.yaml", content)
                self.assertTrue(content.endswith("\n"))

    def test_generated_artifacts_match_renderer_output(self):
        renderer = load_renderer()
        manifest = renderer.load_manifest(MANIFEST_PATH)
        rendered = renderer.render_all(manifest)

        for rel_path, expected in rendered.items():
            with self.subTest(path=rel_path):
                actual = (REPO_ROOT / rel_path).read_text()
                self.assertEqual(actual, expected)

    def test_generated_artifacts_preserve_privacy_and_capability_policy(self):
        renderer = load_renderer()
        manifest = renderer.load_manifest(MANIFEST_PATH)
        rendered = renderer.render_all(manifest)

        soul = rendered["hermes/SOUL.md"]
        config = rendered["deploy/relationship/config.yaml.example"]
        maintain = rendered["scripts/brain-maintain.sh"]

        self.assertIn("Private dirs (people, self, contexts, data) не импортируются", soul)
        self.assertIn("## Онбординг / первый запуск", soul)
        self.assertIn("protocols/onboarding.md", soul)
        self.assertIn("data/raw/", soul)
        self.assertIn("переработай инбокс", soul)
        self.assertIn("self/interview-progress.md", soul)
        self.assertIn("## Паттерны / повторяющиеся темы", soul)
        self.assertIn("protocols/multi-lens-read.md / protocols/pattern-review.md", soul)
        self.assertIn("в базе пока нет данных", soul)
        self.assertIn("Owner: `you`", soul)
        self.assertIn("Canonical home: `/opt/data/owners/you/profiles/relationship`", soul)
        self.assertIn("# Owner: you", config)
        self.assertIn("# Canonical home: /opt/data/owners/you/profiles/relationship", config)
        self.assertIn("mode: disabled", config)
        self.assertIn("corpus: public_only", config)
        self.assertIn("for d in attachment ifs schema-therapy communication systemic family", maintain)
        self.assertNotIn("people/", maintain)

    def test_contract_validator_rejects_unsafe_manifest_variants(self):
        renderer = load_renderer()
        manifest = renderer.load_manifest(MANIFEST_PATH)

        with_private_import = copy.deepcopy(manifest)
        with_private_import["knowledge"]["public_index_dirs"].append("people")
        self.assertTrue(
            any(
                "private dirs listed as public_index_dirs" in error
                for error in renderer.validate_contract(with_private_import, REPO_ROOT)
            )
        )

        browser_without_domains = copy.deepcopy(manifest)
        browser_without_domains["runtime"]["browser"]["mode"] = "local_cdp"
        self.assertTrue(
            any(
                "browser mode requires allowed_domains" in error
                for error in renderer.validate_contract(browser_without_domains, REPO_ROOT)
            )
        )

        unsafe_synthesis = copy.deepcopy(manifest)
        unsafe_synthesis["knowledge"]["synthesis"]["corpus"] = "all"
        self.assertTrue(
            any(
                "synthesis corpus must remain public_only" in error
                for error in renderer.validate_contract(unsafe_synthesis, REPO_ROOT)
            )
        )

        wrong_owner_home = copy.deepcopy(manifest)
        wrong_owner_home["profile"]["canonical_home"] = "/opt/data/owners/alice/profiles/relationship"
        self.assertTrue(
            any(
                "profile.canonical_home must be /opt/data/owners/you/profiles/relationship" in error
                for error in renderer.validate_contract(wrong_owner_home, REPO_ROOT)
            )
        )

        wrong_compat_home = copy.deepcopy(manifest)
        wrong_compat_home["profile"]["compatibility_home"] = "/opt/data/profiles/other"
        self.assertTrue(
            any(
                "profile.compatibility_home must be /opt/data/profiles/relationship" in error
                for error in renderer.validate_contract(wrong_compat_home, REPO_ROOT)
            )
        )

    def test_check_script_runs_full_contract(self):
        result = subprocess.run(
            ["bash", "scripts/check-hermes-profile.sh"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("hermes profile OK", result.stdout)
        self.assertIn("structure OK", result.stdout)
        self.assertIn("privacy OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
