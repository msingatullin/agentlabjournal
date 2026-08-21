import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-article-cycle-isolated.py"


class ArticleCycleIsolationTests(unittest.TestCase):
    def test_cycle_runs_from_fresh_remote_clone(self):
        spec = importlib.util.spec_from_file_location("article_cycle_isolated", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as directory:
            result = module.run_isolated(Path(directory), run=run)

        self.assertEqual(0, result)
        self.assertEqual(
            ["git", "clone", "--depth", "1", module.REMOTE, str(Path(directory) / "repo")],
            calls[0][0],
        )
        self.assertEqual(
            ["/usr/bin/python3", str(Path(directory) / "repo" / "scripts" / "run-article-cycle.py")],
            calls[1][0],
        )
        self.assertEqual(Path(directory) / "repo", calls[1][1]["cwd"])


if __name__ == "__main__":
    unittest.main()
