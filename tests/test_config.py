import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "mediamtx"


def read_yaml(path):
    result = subprocess.run(
        ["yq", "-o=json", ".", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class AddonConfigurationTests(unittest.TestCase):
    def generate(self, overrides, expect_failure=False):
        options = read_yaml(ADDON / "config.yaml")["options"]
        options.update(overrides)
        with tempfile.TemporaryDirectory() as directory:
            options_path = Path(directory) / "options.json"
            config_path = Path(directory) / "mediamtx.yml"
            options_path.write_text(json.dumps(options))
            command = ["bash", str(ADDON / "rootfs/run.sh")]
            if image := os.environ.get("TEST_ADDON_IMAGE"):
                command = [
                    "docker", "run", "--rm", "--network", "none",
                    "--mount", f"type=bind,src={directory},dst=/data",
                    "-e", "MEDIAMTX_BINARY=/bin/true", image,
                ]
            result = subprocess.run(
                command,
                env={
                    **os.environ,
                    "OPTIONS": str(options_path),
                    "CONFIG": str(config_path),
                    "MEDIAMTX_BINARY": "/usr/bin/true",
                },
                capture_output=True,
                text=True,
            )
            if expect_failure:
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(config_path.exists())
                self.assertNotIn("Starting MediaMTX", result.stdout)
                return None
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(config_path.read_text(), object_pairs_hook=self.unique_keys)

    def unique_keys(self, pairs):
        result = {}
        for key, value in pairs:
            self.assertNotIn(key, result, f"Duplicate configuration key: {key}")
            result[key] = value
        return result

    def test_omitted_path_options_inherit_defaults(self):
        config = self.generate({"record": True, "paths": [{"name": "camera"}]})
        self.assertTrue(config["pathDefaults"]["record"])
        self.assertEqual(config["paths"]["camera"], {})

    def test_all_path_options_preserve_values_and_types(self):
        path = {
            "name": "~^camera: #one$",
            "source": "rtsp://camera.invalid/live?video&audio=aac",
            "source_fingerprint": "12:ab",
            "source_protocol": "tcp",
            "source_on_demand": False,
            "source_on_demand_start_timeout": "10s",
            "source_on_demand_close_after": "5s",
            "max_readers": 0,
            "override_publisher": False,
            "rtsp_transport": "tcp",
            "rtsp_any_port": False,
            "rtsp_range_type": "clock",
            "rtsp_range_start": "20260101T000000Z",
            "source_redirect": "rtsp://camera.invalid/other",
            "record": False,
            "record_path": "/media/nas/camera: #one/%path",
            "record_format": "fmp4",
            "record_part_duration": "1s",
            "record_segment_duration": "1h",
            "record_delete_after": "0s",
            "run_on_init": "printf 'init: #ready'",
            "run_on_init_restart": False,
            "run_on_demand": "printf demand",
            "run_on_demand_restart": False,
            "run_on_demand_start_timeout": "10s",
            "run_on_demand_close_after": "5s",
            "run_on_ready": "printf ready",
            "run_on_ready_restart": False,
            "run_on_read": "printf read",
            "run_on_read_restart": False,
        }
        self.assertEqual(set(path), set(read_yaml(ADDON / "config.yaml")["schema"]["paths"][0]))
        config = self.generate({"paths": [path]})
        self.assertEqual(config["paths"][path["name"]], {
            "source": path["source"],
            "sourceFingerprint": "12:ab",
            "sourceProtocol": "tcp",
            "sourceOnDemand": False,
            "sourceOnDemandStartTimeout": "10s",
            "sourceOnDemandCloseAfter": "5s",
            "maxReaders": 0,
            "overridePublisher": False,
            "rtspTransport": "tcp",
            "rtspAnyPort": False,
            "rtspRangeType": "clock",
            "rtspRangeStart": "20260101T000000Z",
            "sourceRedirect": "rtsp://camera.invalid/other",
            "record": False,
            "recordPath": "/media/nas/camera: #one/%path",
            "recordFormat": "fmp4",
            "recordPartDuration": "1s",
            "recordSegmentDuration": "1h",
            "recordDeleteAfter": "0s",
            "runOnInit": "printf 'init: #ready'",
            "runOnInitRestart": False,
            "runOnDemand": "printf demand",
            "runOnDemandRestart": False,
            "runOnDemandStartTimeout": "10s",
            "runOnDemandCloseAfter": "5s",
            "runOnReady": "printf ready",
            "runOnReadyRestart": False,
            "runOnRead": "printf read",
            "runOnReadRestart": False,
        })

    def test_credentials_and_recording_paths_are_literal_strings(self):
        password = 'true: #secret\n"quoted"\\value'
        config = self.generate({
            "auth_enabled": True,
            "publish_user": "null",
            "publish_pass": password,
            "record_path": "/media/nas/camera: #one/%path",
        })
        self.assertEqual(config["pathDefaults"]["recordPath"], "/media/nas/camera: #one/%path")
        self.assertEqual(config["authInternalUsers"][0]["user"], "null")
        self.assertEqual(config["authInternalUsers"][0]["pass"], password)
        self.assertEqual(config["authInternalUsers"][1]["pass"], password)
        self.assertEqual(config["authInternalUsers"][2]["ips"], ["127.0.0.1", "::1"])

    def test_custom_yaml_deeply_overrides_generated_options(self):
        config = self.generate({
            "record": True,
            "paths": [{"name": "camera", "source": "rtsp://camera.invalid/live", "record": True}],
            "custom_config": """
logLevel: debug
pathDefaults:
  record: false
  recordSegmentDuration: 5m
paths:
  camera:
    record: false
    maxReaders: 0
  other:
    source: publisher
authInternalUsers:
  - user: custom
    pass: ''
    ips: []
    permissions:
      - action: read
""",
        })
        self.assertEqual(config["logLevel"], "debug")
        self.assertIs(config["pathDefaults"]["record"], False)
        self.assertEqual(config["pathDefaults"]["recordFormat"], "fmp4")
        self.assertEqual(config["pathDefaults"]["recordSegmentDuration"], "5m")
        self.assertEqual(config["paths"]["camera"], {
            "source": "rtsp://camera.invalid/live", "record": False, "maxReaders": 0,
        })
        self.assertEqual(config["paths"]["other"], {"source": "publisher"})
        self.assertEqual([user["user"] for user in config["authInternalUsers"]], ["custom"])

    def test_invalid_custom_yaml_never_starts_server(self):
        for custom in ["paths: [", "[]", "true", "---\n{}\n---\n{}", "paths: {}\npaths: {}", "paths:\n  camera:\n    record: true\n    record: false"]:
            with self.subTest(custom=custom):
                self.generate({"custom_config": custom}, expect_failure=True)

    def test_empty_custom_yaml_keeps_default_publisher_path(self):
        for custom in ["", "# comment only", "---\n", "null", "~"]:
            with self.subTest(custom=custom):
                self.assertEqual(self.generate({"custom_config": custom})["paths"], {"all_others": {}})

    @unittest.skipUnless(os.environ.get("TEST_ADDON_IMAGE"), "set TEST_ADDON_IMAGE for a real MediaMTX smoke test")
    def test_mediamtx_starts_with_generated_configuration(self):
        options = read_yaml(ADDON / "config.yaml")["options"]
        options.update({
            "paths": [{"name": "camera", "source": "publisher", "max_readers": 0, "record": False}],
            "custom_config": "pathDefaults:\n  recordSegmentDuration: 5m\npaths:\n  camera:\n    overridePublisher: false\n",
        })
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "options.json").write_text(json.dumps(options))
            container = subprocess.check_output([
                "docker", "run", "-d", "--network", "none",
                "--mount", f"type=bind,src={directory},dst=/data",
                os.environ["TEST_ADDON_IMAGE"],
            ], text=True).strip()
            try:
                deadline = time.monotonic() + 10
                logs = ""
                while time.monotonic() < deadline:
                    logs = subprocess.check_output(["docker", "logs", container], text=True, stderr=subprocess.STDOUT)
                    if "[RTSP] started with listeners" in logs:
                        break
                    time.sleep(0.1)
                self.assertIn("[RTSP] started with listeners", logs)
                time.sleep(0.2)
                running = subprocess.check_output([
                    "docker", "inspect", "--format", "{{.State.Running}}", container,
                ], text=True).strip()
                self.assertEqual(running, "true", logs)
            finally:
                subprocess.run(["docker", "rm", "-f", container], check=True, capture_output=True)

    @unittest.skipUnless(os.environ.get("TEST_ADDON_IMAGE"), "set TEST_ADDON_IMAGE for runtime timezone checks")
    def test_runtime_honors_timezone_and_daylight_saving(self):
        cases = [
            ("America/Los_Angeles", "1704067200", "2023-12-31_16-00-00-0800"),
            ("America/Los_Angeles", "1719792000", "2024-06-30_17-00-00-0700"),
            ("America/New_York", "1704067200", "2023-12-31_19-00-00-0500"),
            ("America/New_York", "1719792000", "2024-06-30_20-00-00-0400"),
            ("Europe/Warsaw", "1704067200", "2024-01-01_01-00-00+0100"),
            ("Europe/Warsaw", "1719792000", "2024-07-01_02-00-00+0200"),
            ("Asia/Tokyo", "1704067200", "2024-01-01_09-00-00+0900"),
            ("Asia/Tokyo", "1719792000", "2024-07-01_09-00-00+0900"),
        ]
        for timezone, timestamp, expected in cases:
            with self.subTest(timezone=timezone, timestamp=timestamp):
                result = subprocess.run([
                    "docker", "run", "--rm", "--network", "none",
                    "-e", f"TZ={timezone}", "--entrypoint", "date",
                    os.environ["TEST_ADDON_IMAGE"],
                    "-d", f"@{timestamp}", "+%Y-%m-%d_%H-%M-%S%z",
                ], check=True, capture_output=True, text=True)
                self.assertEqual(result.stdout.strip(), expected)

    def test_blank_transports_keep_defaults(self):
        for value in [None, "", "   ", "udp, tcp"]:
            with self.subTest(value=value):
                config = self.generate({"rtsp_transports": value})
                expected = ["udp", "tcp"] if value == "udp, tcp" else ["udp", "multicast", "tcp"]
                self.assertEqual(config["rtspTransports"], expected)

    def test_default_recording_path_groups_days_and_includes_timezone(self):
        config = self.generate({})
        self.assertEqual(
            config["pathDefaults"]["recordPath"],
            "/media/recordings/%path/%Y-%m-%d/%Y-%m-%d_%H-%M-%S.%f%z",
        )

    def test_media_volume_is_writable(self):
        manifest = read_yaml(ADDON / "config.yaml")
        self.assertIn("media:rw", manifest.get("map", []))


if __name__ == "__main__":
    unittest.main()
