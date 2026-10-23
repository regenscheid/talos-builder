# Image Factory schematics

The non-Pi 5 nodes run stock Talos from [Image Factory](https://factory.talos.dev).
These are their schematics. The factory picks each extension's version from
the siderolabs/extensions catalog for the requested Talos version, so the
files list names only.

| File | Nodes | Replaces |
|---|---|---|
| `cm4-rpi-generic.yaml` | rpi-talos-master, rpi-talos-worker1 (CM4) | `f8a903f1…` (iscsi-tools, util-linux-tools) |
| `amd64-intel.yaml` | rpi-talos-worker9, talos-9sm-s68, talos-dhm-eve, talos-s74-qez | `613e1592…` (iscsi-tools, util-linux-tools) and `36cd6536…` (+ intel-ucode, worker9 only) |

Get a schematic ID (the factory stores the schematic and returns its hash):

```bash
curl -sX POST --data-binary @schematics/amd64-intel.yaml https://factory.talos.dev/schematics
```

The installer is then `factory.talos.dev/metal-installer/<id>:<talos version>`.

## Extensions that do not fit every node

| Extension | amd64 | CM4 | Pi 5 / CM5 (custom build) | Why |
|---|---|---|---|---|
| `kata-containers` | yes | **no** | **no** | The extension runs VMs on cloud-hypervisor, which on ARM KVM requires a GICv3. BCM2711 and BCM2712 both have a GICv2 (GIC-400). The extension ships no QEMU and registers only the `kata` handler, so there is no `kata-qemu` to fall back to; that would take a custom extension (see below). |
| `gvisor` | yes | yes | **no** | gVisor's arm64 build assumes 4K pages (a 64K build exists, no 16K). The Pi 5 vendor kernel uses 16K pages; the stock CM4 kernel uses 4K. |
| `intel-ucode` | yes | n/a | n/a | All four amd64 nodes are Intel. |

Because the runtimes are not on every node, give each RuntimeClass a
`scheduling.nodeSelector`; otherwise a pod using it can land on a node that
lacks the handler. For kata, `kubernetes.io/arch: amd64` is enough. gVisor
needs a label on the nodes that have it. The kata README's `overhead` of
130Mi is far below the 2048 MiB VM the extension's `configuration.toml`
gives each pod by default.

A `kata-qemu` extension for the Pis would copy `qemu-system-aarch64` and its
data files from the same kata-static tarball (the arm64 tarball includes
QEMU), add a QEMU `configuration.toml` and register a `kata-qemu` runtime.
Kata's arm64 QEMU machine uses `gic-version=host`, so GICv2 is not a blocker
there. It is untested on these boards (16K host pages and the CM5's 40-bit
IPA limit are the open questions). It could only reach the CM4s by moving
them off Image Factory, which accepts official extensions only.

Extensions shipping kernel modules (drbd, zfs, gasket, nvidia, …) are built
for the stock Talos kernel and will not load on the Pi 5 custom kernel
(`module.sig_enforce=1`).
