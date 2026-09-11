# Manual package installation

You need Omarchy on x86-64 and the supported fingerprint reader. The sudo setup
uses Omarchy's laptop-lid helper and the standard `auth include system-auth`
PAM configuration.

Install the plugin checkout as described in the README. In a visible terminal,
run its package installer without opening the panel:

```sh
python3 -I scripts/plugin.py install
```

This is the same checksum-pinned release installation as the panel. It requires
the release asset to have been published and the documented runtime dependencies
to be present. It installs under `/opt/t480fingerprint` without building source.
For contributor source builds, see [testing](testing.md); those use your local
toolchain and are separate from the released artifact.

## Prepare and enable sudo

From the source checkout, run `./scripts/setup-sudo.sh`. This combined workflow
enrolls or reuses your right index fingerprint, verifies it, then enables
fingerprint sudo with password fallback. For another finger, use
`./scripts/setup-sudo.sh --finger left-index-finger`.

For separate preparation and activation through the settings panel, return to
[the main guide](../README.md#use). See [sudo integration](sudo-auth.md) for
configuration details and recovery.
