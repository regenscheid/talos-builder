# Maintenance release contract

The extension-bearing installer is published as
`ghcr.io/regenscheid/talos-builder/installer:<release>-arm64-extensions`.
Release notes now reference that artifact exactly. On 2026-09-26, the existing
unsuffixed `v1.13.8-rpi5-rc2` installer returned MANIFEST_UNKNOWN; the suffixed image
resolved to `sha256:bd72bee62849ecae01701d8a5b60cdb949db49cd40d326d7298639793dc2c257`.

Builds publish `release-manifest.json` with expected runtime version, source/kernel/
overlay/config/module identities and resolved extension/installer digests. Its state
is always `built-unvalidated`. Runtime expectation comes from the existing build tag;
an actual hardware observation is still required.

Tuppr replaces an installer's tag with the requested runtime version. The measured CM5
runtime is `v1.13.8-rpi5-rc2`, without the `-arm64-extensions` packaging suffix. A
runtime-matching alias must reference the verified extension-bearing artifact.

`scripts/promote-runtime-alias.py` previews that mapping by default. It requires a
hardware-observed runtime, an evidence JSON binding runtime/extensions/reviewer to
the exact installer digest, and refuses to overwrite an existing different digest.
The separate `--publish` flag is required for registry mutation. This task did not
publish any alias, release, image, or upgrade. Alias publication itself is not fleet
approval; maintenance promotion remains a separate review.

Treat promoted aliases as immutable using registry access controls. Keep prior artifacts
available independently of the cluster. A rebuilt image with unchanged runtime needs
an explicit reinstall procedure; ordinary version reconciliation may skip it.

Longhorn is on the same NVMe as the boot disk on this cluster. Future upgrades must
preserve EPHEMERAL and user-volume data. Never substitute fresh install/reset/raw-disk
flashing for the normal, data-preserving Talos upgrade path.
