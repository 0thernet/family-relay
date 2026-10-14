import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("check_container", Path(__file__).resolve().parents[1] / "scripts" / "check-container.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def result(code=0, output=""):
    return subprocess.CompletedProcess([], code, output, "")


class ContainerCleanupTests(unittest.TestCase):
    def test_launch_timeout_reconciles_preassigned_name_and_cleans_container(self):
        with mock.patch.object(check, "command", side_effect=[result(output="container-id\n"), result(), result()]) as command:
            with self.assertRaises(subprocess.TimeoutExpired):
                with check.owned_container() as name:
                    raise subprocess.TimeoutExpired(["docker", "run", "--name", name], 60)
        self.assertEqual(command.call_args_list, [
            mock.call(["docker", "ps", "--all", "--quiet", "--filter", "name=^/" + name + "$"]),
            mock.call(["docker", "stop", "--time", "5", name]),
            mock.call(["docker", "rm", "--force", name]),
        ])

    def test_no_container_created_needs_no_stop_or_remove(self):
        with mock.patch.object(check, "command", return_value=result()) as command:
            with check.owned_container():
                pass
        self.assertEqual(command.call_count, 1)

    def test_shutdown_timeout_still_removes_owned_container(self):
        responses = [result(output="container-id\n"), subprocess.TimeoutExpired(["docker", "stop"], 60), result()]
        with mock.patch.object(check, "command", side_effect=responses) as command:
            with self.assertRaises(subprocess.TimeoutExpired):
                with check.owned_container() as name:
                    pass
        self.assertEqual(command.call_args, mock.call(["docker", "rm", "--force", name]))

    def test_reconciliation_error_is_never_mistaken_for_absent_container(self):
        with mock.patch.object(check, "command", return_value=result(code=1)):
            with self.assertRaisesRegex(RuntimeError, "Could not reconcile"):
                with check.owned_container():
                    pass


if __name__ == "__main__":
    unittest.main()
