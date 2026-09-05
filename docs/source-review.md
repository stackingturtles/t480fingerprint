# Source review — 2026-09-05

Driver source: https://gitlab.freedesktop.org/libfprint/libfprint.git
MR: https://gitlab.freedesktop.org/libfprint/libfprint/-/merge_requests/626
Commit: `0fd78560a245eebec1c93e71ee1f29b15ec1be67`, LGPL-2.1-or-later.
MR state from GitLab API: opened. This is an experimental, unmerged driver.
The commit message reports enroll/verify testing on an X280 with the same USB ID;
that is upstream evidence, not a completed test on tank.

Runtime data source: https://gitlab.freedesktop.org/ggiesen/libfprint-validity-data.git
Commit: `4b03b2a1e607b4fea4b7a447644aaf02aa92e2e7`, MIT.
Generated and verified locally using its Makefile. Its HMAC key is public and
only detects corruption; it does not authenticate publisher provenance. Generic
upstream data is distinct from private sensor pairing/enrollment state. No
runtime data or vendor firmware was installed during these tests.

## Reviewed boundaries

- `validity.c:dev_probe`: USB reset, interface claim and GET_VERSION query.
  It reads a serial internally; our tool suppresses identifiers and debug output.
- `validity.c:dev_open` enters initialization, runtime blob loading, pairing,
  TLS and optional firmware extension upload. This is not a read-only operation.
- `validity_pair.c:pair_check_needed` starts pairing on empty flash;
  `pair_verify_tls_recv` starts pairing if existing TLS blocks are missing.
- `pair_partition_flash_recv` enters factory-reset states after status 0x0404
  (existing partitions). `PAIR_FACTORY_RESET_SEND` issues the reset command.
  Later pairing states erase/write partitions. This needs a guard or specific
  user authorization before opening an unknown-state sensor.
- The laboratory probe deliberately never calls fp_device_open, enrollment,
  deletion or storage clearing. Our new code compiles with -Wall -Wextra -Werror.
- System fprintd remains installed, preserving its authentication framework;
  open-fprintd was not installed. The lab has no PAM integration.

This is a focused review of testing/initialization boundaries, not a complete
security audit of the driver, protocol, or cryptography.

## Guarded interactive build

`patches/0001-guard-sensor-initialization.patch` is applied to a separate Git
worktree, keeping the upstream checkout intact. It rejects initial pairing and
re-pairing when TLS keys are absent, rejects factory reset, clean-slate setup and
firmware extension upload, and loads the packaged data under
`/opt/t480fingerprint/share/validity`. The build verifies the worktree diff is
exactly this recorded patch. This protects startup paths; it does not make the
enrollment operation read-only.

The interactive tool opens normally, creates one uniquely named temporary sensor
record, verifies against the returned FpPrint reference, and calls delete_print
only for that new record. It never calls clear_storage or saves template/image
files. Upstream enrollment explicitly preserves other enrolled users/fingers.
Cleanup failure is reported separately and cannot produce a final success.
The native driver can reclaim the database partition when deleting its last
print; no bulk-clear API is invoked by the tool.

Runtime data is now included in the isolated package (-2); vendor firmware
remains absent. Eight workflow tests pass and the guarded upstream suite passes
99 entries with 32 skips, including the 172-case Validity unit test.
