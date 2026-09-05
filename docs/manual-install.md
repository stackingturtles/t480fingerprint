# Manual package installation

You need Omarchy on x86-64 and the supported fingerprint reader. The sudo setup
uses Omarchy's laptop-lid helper and the standard `auth include system-auth`
PAM configuration.

Install the build, test and authentication dependencies:

```sh
sudo pacman -S --needed base-devel git meson ninja glib2-devel \
  gobject-introspection libgusb libgudev openssl cairo pixman umockdev \
  python python-cairo python-gobject python-mako python-markdown python-tqdm \
  fprintd uv
```

Clone the repository, build as your regular user, and install the package:

```sh
git clone https://github.com/stackingturtles/t480fingerprint.git
cd t480fingerprint
./scripts/build-interactive.sh
./scripts/test.sh
./scripts/package.sh
sudo pacman -U build/package/t480fingerprint-lab-1.94.100.r626.0fd7856-5-x86_64.pkg.tar.zst
```

The build fetches pinned driver and runtime-data sources. The package installs
under `/opt/t480fingerprint`; sudo setup loads its driver through a local
`fprintd` service override and backs up configuration before changing it.

## Prepare and enable sudo

From the source checkout, run `./scripts/setup-sudo.sh`. This combined workflow
enrolls or reuses your right index fingerprint, verifies it, then enables
fingerprint sudo with password fallback. For another finger, use
`./scripts/setup-sudo.sh --finger left-index-finger`.

For separate preparation and activation through the settings panel, return to
[the main guide](../README.md#use). See [sudo integration](sudo-auth.md) for
configuration details and recovery.
