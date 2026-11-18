# Kleinia integration notes

The Kleinia GUI installer = this fork's `readymade` binary, packaged as the
`kleinia-installer` RPM (see `dist/nfpm.yaml`). Distro-facing config lives in
the [kleinia](https://github.com/kleinia-os/kleinia) assembly repo (`files/`):
`/etc/readymade.toml` (source default, `src/cfg.rs`), repart-cfgs under
`/usr/share/readymade/repart-cfgs/` (`crates/libreadymade/consts.rs`), and the
desktop entries. The copies in `runtime/` and `images.json` here are reference
snapshots of that config — the assembly repo is the source of truth.

## Status
- [x] Builds on Fedora 44 toolchain (Rust/Helium via the Terra repo)
- [x] Installs Kleinia bootc image (offline embedded payload)
- [x] End-to-end verified: partition → deploy → GRUB → first boot (2026-10)
- [x] ISO integration replaces Calamares (kleinia repo N4)
- [ ] Upstream: rebase onto newer upstream / propose fixes upstream

Upstream: https://github.com/FyraLabs/readymade (GPL-3.0-or-later)
