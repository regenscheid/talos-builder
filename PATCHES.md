# Patch inventory

What each patch in this repo does, whether it is still needed, and when it can
go. Checked against upstream on 2026-10-22, with the 1.14 port on 2026-10-23;
re-check before each upgrade.

Cluster at the time: 4x CM5 Lite on a DeskPi Super6C, NVMe boot, running
`v1.13.8-rpi5-rc2` (vendor kernel 6.18.29). Over 55 days of uptime the kernel
log showed 1 macb TX stall (recovered), 0 link drops, 0 NVMe/AER errors and 0
`mmc0` timeouts.

## Why a custom build is still needed

* **Networking.** Stock Talos (mainline kernel + upstream macb fixes) still
  shows frequent macb TX stalls on Pi 5/CM5 under load. Reports on
  [sbc-raspberrypi#91](https://github.com/siderolabs/sbc-raspberrypi/issues/91)
  from 1.13.9, 1.13.10 and 1.14.1 range from one every ~10 minutes (with
  EEE/TSO off) to ~170/hour/node.
* **NVMe boot.** The upstream overlay's U-Boot has no RP1/PCIe support, so a
  CM5 Lite cannot boot from NVMe. The fixes are only in open PRs
  ([#88](https://github.com/siderolabs/sbc-raspberrypi/pull/88),
  [#97](https://github.com/siderolabs/sbc-raspberrypi/pull/97)); upstream
  wants them reviewed on the U-Boot list first. The `rpiboot202607` overlay
  branch carries them.

## Kernel source: `patches/siderolabs/pkgs/0001`

Switches the pkgs kernel to `raspberrypi/linux` (pinned commit) and replaces
`kernel/build/config-arm64` with a vendor-kernel config.

| | |
|---|---|
| Needed | Yes — this is the vendor kernel |
| Pin | `rpi-6.18.y` @ `a72a0085` (6.18.29, 2026-05-13) |
| Upstream now | `rpi-6.18.y` is at 6.18.58 (2026-10-21) |
| Applies to | pkgs `2ec10eb` (`release-1.14`, what Talos v1.14.4 pins). The release-1.13 version applied to `969f61c` only |

### Porting the config to a new pkgs commit

The config is a full normalized `.config`, so it has to be regenerated rather
than rebased. For 1.14 (2026-10-23):

1. Take the option changes the old patch makes relative to its base
   (`969f61c` `config-arm64` → patched): 447 options.
2. Apply those to the new base's `config-arm64` (`2ec10eb`). Only 15 options
   were touched by both the patch and upstream, and they agreed.
3. Keep `MMC_SDHCI=y`: upstream 1.14 made it `m`, which would have capped the
   SD/eMMC host drivers the patch builds in.
4. Normalize with `make ARCH=arm64 LLVM=1 olddefconfig` against the vendor
   source *after* the kernel patches are applied (0017 adds
   `LOCK_DOWN_IN_EFI_SECURE_BOOT`), using the pkgs toolchain itself
   (`ghcr.io/siderolabs/tools` + `ghcr.io/siderolabs/llvm` at pkgs'
   `TOOLS_REV`). An older clang silently drops options such as
   `KSTACK_ERASE`, which the hardening gate then rejects.
5. Check with pkgs' pinned `kernel-hardening-checker` (`kspp_ref`) and
   `kernel/build/scripts/filter-hardened-check.py`.

Net effect versus the 1.13 kernel config, beyond upstream's own 1.13→1.14
changes: the vendor `FB_RPISENSE`/`FB_BCM2708` fbdev drivers go (upstream
dropped `FB` for simpledrm), and `AQTION`, `HID_CHICONY`, `HID_SAMSUNG`
become modules.

What the vendor kernel already contains at the pin: the macb v1 TX-stall
series (`a9e13da2`, `ff6914e9`, `79dc190b`), MAC-side EEE/LPI support
(`8a15cb90`, `70d75c74`, `f6c4ee98`), and the DTS change that re-enables EEE
(`6855d494`).

## Kernel patches: `patches/linux/`

These are applied on top of the vendor kernel. The `patches-linux` recipe
deletes the mainline macb patches from the pkgs tree first, since the vendor
tree has its own copies. On `release-1.14` that includes `0008`–`0011` (the
mainline macb EEE backport, already in the vendor tree; `0009` would fail to
apply). The remaining pkgs patches (`0004` PCI, `0012`–`0015` libceph, `0017`
lockdown, `0018` efistub) apply to the vendor tree.

| Patch | What it does | Upstream (`rpi-6.18.y`) | At next vendor-kernel bump |
|---|---|---|---|
| `0001-net-macb-gate-PCIe-posted-write-flush` | Limits the TSTART readback to RP1 (`MACB_CAPS_PCIE_POSTED_WRITES`) | Merged 2026-06-17 (`b1b307c0`), still there | **Drop** — already in tree |
| `0002-net-macb-drop-destructive-ISR-read` | Replaces the v1 ISR read (read-to-clear on RP1) with an IMR barrier | Merged 2026-06-17, **reverted 2026-07-14** (`86a1889a`) | **Drop** — no longer applies; the v1 code it fixes was also reverted |
| `0003-net-macb-gate-TX-stall-watchdog` | Limits the 1 Hz TX-stall watchdog to carrier-up, rate-limits the warning | Merged 2026-06-17, **reverted 2026-07-14** (`d57db18e`) | **Drop** — replaced by the mainline `ndo_tx_timeout` recovery (`e438ec3e`, backported as `68af74ad`) |
| `0006-arm64-dts-bcm2712-disable-EEE-on-rp1` | Marks the PHY EEE-broken (`eee-broken-1000t/100tx`) on Pi 5 and CM5 | Raspberry Pi deliberately removed these on 2026-03-09 (`6855d494`) once the MAC gained EEE support | **Keep, rebase** — context changed; still the conservative choice while #91 is open. Some on #91 use `configTxtAppend: dtparam=eee=off` instead (not verified against the vendor DTB's overrides) |

`patches/linux/README.md` predates this: it lists 0004/0005 PCI patches that
are not in the directory and describes 0006 as a forward-port gap, which it is
not.

## Talos: `patches/siderolabs/talos/`

| Patch | What it does | Needed | v1.13.12 | v1.14.4 |
|---|---|---|---|---|
| `0001-Patched-for-Raspberry-Pi-5` | Replaces `hack/modules-arm64.txt` with the vendor-kernel module list for the initramfs | Yes, while on the vendor kernel. Regenerate when the module set changes | Applies (release-1.13 version) | Regenerated on the `talos-1.14` branch |
| `0002-Makefile` | `SED ?= sed` for macOS (`gsed`) builds | Only for local macOS builds; CI is Linux | Applies (release-1.13 version) | Rebased on the `talos-1.14` branch |

The list is also what ships: Talos copies only listed modules into the image.
The 1.14 list is the 1.13 list plus every module on upstream's 1.14 list that
the vendor build actually produces (upstream moved USB host controllers,
virtio, ACPI, several NIC and HID drivers and more from built-in to modules),
minus `cdc-phonet` (Phonet is gone in 1.14) and `sdhci.ko` (kept built in).
Every `.ko` entry must exist in the kernel build, or the Talos image step
fails; a local build on 2026-10-23 confirmed all 310 entries. Built but
unlisted, as upstream: `mhi`, `vc4`, `cachefiles`.

## pkgs: `patches/siderolabs/pkgs/0002-Support-alternative-sed-interpreter`

Same `SED` hook as above, for pkgs. Only matters for macOS builds. Applies to
`release-1.13` and `release-1.14`.

## Overlay: `patches/siderolabs/sbc-raspberrypi/0001` + `rpiboot202607` branch

The patch points the DTB build at the same vendor kernel commit, skips the
mainline-compat DTB patches, and drops `gpu_mem`/`hdmi_safe` from config.txt.
Needed for as long as the kernel is the vendor kernel. Keep
`raspberrypi_kernel_version` in step with the pkgs kernel pin.

The branch (`v0.2.0` + 7 commits, tip `0995597`) adds a dedicated `rpi_5`
U-Boot 2026.07 with the bcm2712/RP1 series. Still needed for NVMe boot.

Upstream overlay changes since `v0.2.0` (`v0.2.1`, `v0.2.2`) are DTB fixes so
the **mainline** kernel works with vendor DTBs (CM5 Ethernet MDIO layout, Pi 5
compatible strings). They are not needed while the DTBs come from the vendor
kernel itself.

## Upstream issues checked

| Issue | Affects this cluster? |
|---|---|
| [#81](https://github.com/siderolabs/sbc-raspberrypi/issues/81) Pi 5 NVMe/U-Boot | Yes — covered by the `rpiboot202607` branch |
| [#82](https://github.com/siderolabs/sbc-raspberrypi/issues/82) / [#91](https://github.com/siderolabs/sbc-raspberrypi/issues/91) Ethernet dies (EEE, macb TX stall) | Yes — covered by the vendor kernel + `0001`–`0003` + `0006`; still open upstream |
| [#92](https://github.com/siderolabs/sbc-raspberrypi/issues/92) CM5 `broken-cd` → `mmc0` timeouts with no SD card | No symptom observed (0 timeouts in 55 days), even though `broken-cd` is still in the vendor dtsi. No patch needed |
| [PR #98](https://github.com/siderolabs/sbc-raspberrypi/pull/98) CM5 Lite SD init | No — these nodes boot from NVMe |

## Upgrade paths

1. **Talos v1.13.12, same kernel.** Done: `v1.13.12-rpi5-rc2`, on all four
   CM5s since 2026-10-23. CI reused the published kernel
   (`k1-969f61c-200deb333938`).
2. **Vendor kernel bump (6.18.29 → current `rpi-6.18.y`).** Update the pin and
   sha in pkgs `0001` and the overlay patch; drop linux `0001`–`0003`; rebase
   `0006`; regenerate the module list if the module set changed; ~70 min
   kernel build. Picks up ~29 stable releases and the reviewed upstream TX
   recovery, but it changes the driver that is currently stable, so soak it on
   one node.
3. **Talos v1.14.4.** Ported on the `talos-1.14` branch, keeping the 6.18.29
   vendor kernel so only one thing changes at a time; the kernel bump (2) can
   follow separately. `PKG_COMMIT` is `2ec10eb`, the pkgs config is
   regenerated as described above, and `KERNEL_EPOCH` is 2, so CI builds a
   new kernel (~70 min). Not yet built in CI or deployed.
