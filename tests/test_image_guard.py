"""Recovery must use the recorded local image, without rebuilding or pulling."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMAGE_ID = "sha256:" + "a" * 64


class ImageGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.release = self.root / "release-1"
        self.release.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        docker = self.bin / "docker"
        docker.write_text('#!/usr/bin/env bash\n[[ "$*" == "image inspect --format {{.Id}} family-relay:release-1" ]] || exit 91\n[[ ${IMAGE_MISSING:-} != 1 ]] || exit 1\nprintf "%s\\n" "$IMAGE_ID"\n')
        docker.chmod(0o755)

    def tearDown(self):
        self.temporary.cleanup()

    def invoke(self, operation, **environment):
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], IMAGE_ID=IMAGE_ID, **environment)
        return subprocess.run(["bash", "-c", 'source "$1"; "$2" "$3"', "check", str(ROOT / "scripts/image-guard.sh"), operation, str(self.release)], env=env, capture_output=True, text=True, timeout=5)

    def test_record_and_recover_exact_image(self):
        self.assertEqual(self.invoke("record_release_image").returncode, 0)
        self.assertEqual((self.release / ".image-id").read_text().strip(), IMAGE_ID)
        self.assertEqual(self.invoke("require_release_image").returncode, 0)

    def test_missing_changed_or_unrecorded_image_fails_closed(self):
        self.assertNotEqual(self.invoke("require_release_image").returncode, 0)
        self.assertEqual(self.invoke("record_release_image").returncode, 0)
        self.assertNotEqual(self.invoke("require_release_image", IMAGE_MISSING="1").returncode, 0)
        (self.release / ".image-id").write_text("sha256:" + "b" * 64)
        self.assertNotEqual(self.invoke("require_release_image").returncode, 0)

    def test_record_does_not_overwrite_previous_identity(self):
        self.assertEqual(self.invoke("record_release_image").returncode, 0)
        self.assertNotEqual(self.invoke("record_release_image").returncode, 0)
        self.assertEqual((self.release / ".image-id").read_text().strip(), IMAGE_ID)

    def test_symlink_or_invalid_identity_rejected(self):
        marker = self.release / ".image-id"
        marker.symlink_to(self.root / "missing")
        self.assertNotEqual(self.invoke("record_release_image").returncode, 0)
        self.assertNotEqual(self.invoke("require_release_image").returncode, 0)
        marker.unlink()
        marker.write_text("unexpected")
        self.assertNotEqual(self.invoke("require_release_image").returncode, 0)


if __name__ == "__main__":
    unittest.main()
