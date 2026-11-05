from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

# Keep this test independently importable; do not depend on collection order or
# another test mutating sys.path as a side effect.
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_all_seven_rows import (  # noqa: E402
    ToolUnavailable,
    live_result,
    preserve_ipv6_loopback_capture,
    run_all,
)


class SevenRowsArtifactAuditTests(unittest.TestCase):
    """Offline row-by-row checks; optional tools and local IPv6 capture stay opt-in."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = run_all()
        cls.rows = cls.summary["rows"]

    def test_l1_checks_both_traces_and_preserves_direction(self) -> None:
        row = self.rows["L1_QUIC"]
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(set(row["per_trace"]), {"chromium", "curl"})
        self.assertEqual(row["post_switch_client_dcid_matches"], {
            "quic_chromium": 5,
            "quic_curl": 5,
        })
        self.assertIn("not server-direction", row["direction_interpretation"])

    def test_l2_is_labeled_as_imported_output_comparison(self) -> None:
        row = self.rows["L2_TLS_SECRETS"]
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["evidence_class"], "imported Track 1 JSON comparison")
        self.assertGreater(row["with_keys"]["certificate_records"], 0)
        self.assertGreater(row["with_keys"]["http_records"], 0)
        self.assertTrue(any("not present" in item for item in row["limits"]))

    def test_l3_does_not_infer_proxy_or_offload_causality(self) -> None:
        row = self.rows["L3_VANTAGE_OFFLOAD"]
        self.assertEqual(row["status"], "PASS")
        self.assertFalse(row["offload_toggle_changed_syn_profile"])
        self.assertEqual(row["proxy_or_tcp_termination"], "NOT_ESTABLISHED")

    def test_l4_checks_all_saved_repeats_and_field_lengths(self) -> None:
        row = self.rows["L4_PQ_MLKEM"]
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["arms"]["pq"]["client_hellos"], 5)
        self.assertEqual(row["arms"]["pq"]["tshark_tls_handshake_length_field"], 1511)
        self.assertEqual(row["arms"]["pq"]["selected_server_group_decimal"], "4588")
        self.assertEqual(row["arms"]["classic"]["tshark_tls_handshake_length_field"], 508)
        self.assertTrue(row["ja4_diverges"])
        self.assertTrue(any("does not verify TCP segmentation" in item for item in row["limits"]))

    def test_l5_correlates_saved_grease_values_without_claiming_fresh_runs(self) -> None:
        row = self.rows["L5_GREASE_STABILITY"]
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["client_hello_observations"], 50)
        self.assertEqual(row["distinct_ja3"], 50)
        self.assertEqual(row["distinct_saved_ja4"], 15)
        self.assertEqual(len(row["distinct_first_signature_grease_values"]), 15)
        self.assertTrue(any("not 50 newly generated" in item for item in row["limits"]))

    def test_loopback_capture_preserver_keeps_pcap_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "temporary.pcap"
            payload = bytes(range(40))
            source.write_bytes(payload)
            output_dir = root / "evidence"
            saved = preserve_ipv6_loopback_capture(source, output_dir, run_id="test-run")
            self.assertEqual(saved.read_bytes(), payload)
            self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), hashlib.sha256(payload).hexdigest())
            with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
                preserve_ipv6_loopback_capture(source, output_dir, run_id="test-run")

    def test_l6_empty_pcap_remains_unmeasured(self) -> None:
        row = self.rows["L6_IPV6"]
        self.assertEqual(row["status"], "NOT_MEASURED")
        self.assertEqual(row["committed_capture_bytes"], 24)
        self.assertEqual(row["committed_packet_records"], 0)
        self.assertEqual(row["public_ipv6_egress"], "NOT_TESTED")

    def test_l7_reports_background_names_and_narrow_scope(self) -> None:
        row = self.rows["L7_ECH"]
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["ech_off"]["target_outer_sni_rows"], 2)
        self.assertEqual(row["ech_on"]["public_name_rows"], 2)
        self.assertEqual(row["ech_on"]["target_outer_sni_rows"], 0)
        self.assertTrue(row["other_visible_background_sni"])
        self.assertIn("not present", row["target_flow_correlation"])

    def test_live_statuses_distinguish_unrun_from_missing_dependency(self) -> None:
        self.assertEqual(live_result(lambda: None, enabled=False)["status"], "NOT_RUN")
        def missing_tool() -> None:
            raise ToolUnavailable("test dependency is absent")
        blocked = live_result(missing_tool, enabled=True)
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["reason"], "test dependency is absent")

    def test_json_covers_all_seven_rows_and_separates_live_checks(self) -> None:
        expected = {
            "L1_QUIC", "L2_TLS_SECRETS", "L3_VANTAGE_OFFLOAD", "L4_PQ_MLKEM",
            "L5_GREASE_STABILITY", "L6_IPV6", "L7_ECH",
        }
        self.assertEqual(set(self.rows), expected)
        self.assertEqual(set(self.summary["live_checks"]), expected)
        self.assertEqual(self.summary["schema_version"], 3)
        self.assertEqual(self.summary["overall_live_status"], "INCOMPLETE")
        self.assertTrue(all(item["status"] == "NOT_RUN" for item in self.summary["live_checks"].values()))
        self.assertFalse(self.summary["live_options"]["live_tool_checks_requested"])
        self.assertFalse(self.summary["live_options"]["ipv6_loopback_requested"])

    def test_overall_status_cannot_be_pass_while_l6_is_unmeasured(self) -> None:
        self.assertEqual(self.summary["overall_status"], "INCOMPLETE")
        self.assertEqual(self.summary["exit_code"], 2)
        self.assertIn("no standalone grading rubric", self.summary["course_rubric_note"])


if __name__ == "__main__":
    unittest.main()
