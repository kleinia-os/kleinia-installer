use crate::{
    backend::{mounts::generate_cryptdata, provisioners::filesystem::FileSystemProvisionerModule},
    prelude::*,
};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
pub struct Bootc {
    pub imgref: String,
    pub target_imgref: Option<String>,
    pub enforce_sigpolicy: bool,
    pub kargs: Vec<String>,
    pub args: Vec<String>,
}

impl Bootc {
    /// Call bootc to copy the contents of the container into the target.
    ///
    /// The caller must verify that `self.copy_mode.is_bootc()`.
    ///
    /// # Errors
    ///
    /// Returns an error if `bootc install to-filesystem` fails to run or exits unsuccessfully.
    #[allow(clippy::unwrap_in_result, clippy::needless_pass_by_value)]
    pub fn bootc_copy(&self, target_root: &Path, cryptdata: Option<CryptData>) -> Result<()> {
        let imgref = &self.imgref;
        let target_imgref = &self.target_imgref;
        let enforce_sigpolicy = &self.enforce_sigpolicy;
        let args = &self.args;

        tracing::info!(imgref=?self.imgref, "running bootc install to-filesystem");

        tracing::warn!("[KLEINIA-DEBUG] bootc_copy: imgref={}, target={:?}", imgref, target_root);
        let bootc_result = std::process::Command::new("bootc")
            .args(["install", "to-filesystem", "--source-imgref", imgref])
            .args(
                (cryptdata.iter())
                    .flat_map(|data| data.cmdline_opts.iter().flat_map(|opt| ["--karg", opt])),
            )
            .arg(target_root)
            .args((target_imgref.iter()).flat_map(|a| ["--target-imgref", a]))
            .args(args.iter().flat_map(|e| ["--karg", e]))
            .args(enforce_sigpolicy.then_some("--enforce-container-sigpolicy"))
            .args(args.iter())
            .status();

        match bootc_result {
            Ok(status) => {
                tracing::warn!("[KLEINIA-DEBUG] bootc exit: {:?}", status.code());
                tracing::warn!("[KLEINIA-DEBUG] bootc stdout: {}", "(inherited)");
                tracing::warn!("[KLEINIA-DEBUG] bootc stderr: {}", "(inherited)");
                if !status.success() {
                    bail!("bootc install failed with exit code {:?}", status.code());
                }
            }
            Err(e) => {
                tracing::warn!("[KLEINIA-DEBUG] bootc spawn error: {:?}", e);
                bail!("failed to spawn bootc: {:?}", e);
            }
        }

        Ok(())
    }

    // This cleans up any folder that is not on the bootc whitelist from a bootc-installed filesystem
    fn bootc_cleanup(mountpoint: &Path) -> Result<()> {
        _ = std::fs::read_dir(mountpoint)?.try_for_each(|f| {
            let f = f?;
            match f.file_name().as_encoded_bytes() {
                b"boot" | b"ostree" | b"efi" | b".bootc-aleph.json" => {}
                _ => {
                    _ = if f.file_type()?.is_dir() {
                        std::fs::remove_dir_all(f.path())
                    } else {
                        std::fs::remove_file(f.path())
                    }
                }
            }
            std::io::Result::Ok(())
        });
        Ok(())
    }
}

impl FileSystemProvisionerModule for Bootc {
    fn run(&self, playbook: &crate::playbook::Playbook, mounts: &Mounts) -> Result<()> {
        let tmproot = tempfile::tempdir()?;
        let bootc_rootfs_mountpoint = tmproot.path();
        let mut sorted_mounts = mounts.clone();
        sorted_mounts.sort_mounts();
        sorted_mounts.mount_all(
            bootc_rootfs_mountpoint,
            playbook
                .encryption
                .as_ref()
                .map(|e| e.encryption_key.as_str()),
        )?;

        tracing::warn!("[KLEINIA-DEBUG] bootc run() started, tmproot={:?}", bootc_rootfs_mountpoint);
        tracing::warn!("[KLEINIA-DEBUG] mounts: {:?}", sorted_mounts);

        // Live env workaround: /var/tmp is on a tiny tmpfs; redirect it to
        // the target disk so bootc can stage image layers there
        let scratch = bootc_rootfs_mountpoint.join("var/tmp");
        std::fs::create_dir_all(&scratch)?;
        let scratch_str = scratch.to_str().unwrap_or_default();
        tracing::warn!("[KLEINIA-DEBUG] var/tmp redirect: mount --bind {} /var/tmp", scratch_str);
        let vt_status = std::process::Command::new("mount")
            .args(["--bind", scratch_str, "/var/tmp"])
            .status();
        tracing::warn!("[KLEINIA-DEBUG] var/tmp redirect result: {:?}", vt_status);

        // Live env workaround: bind /dev into target (bootc needs device nodes)
        let devdir = bootc_rootfs_mountpoint.join("dev");
        std::fs::create_dir_all(&devdir)?;
        let devdir_str = devdir.to_str().unwrap_or_default();
        tracing::warn!("[KLEINIA-DEBUG] /dev bind: mount --rbind /dev {}", devdir_str);
        let dev_status = std::process::Command::new("mount")
            .args(["--rbind", "/dev", devdir_str])
            .status();
        tracing::warn!("[KLEINIA-DEBUG] /dev bind result: {:?}", dev_status);
        // The live /dev is shared-propagation (systemd default): without
        // rslave below, unmounting anything under target/dev later (umount_all,
        // umount -R, cleanup) propagates back and unmounts the LIVE /dev/pts —
        // after which no new pty can be created in the live session
        // ("Failed to create pseudo terminal device"). rslave receives
        // propagation but never sends it back — same trick nspawn/docker use.
        tracing::warn!("[KLEINIA-DEBUG] /dev make-rslave: {}", devdir_str);
        let slave_status = std::process::Command::new("mount")
            .args(["--make-rslave", devdir_str])
            .status();
        tracing::warn!("[KLEINIA-DEBUG] /dev make-rslave result: {:?}", slave_status);
        if !slave_status.map_or(true, |s| s.success()) {
            bail!("mount --make-rslave {} failed — refusing to continue without propagation isolation", devdir_str);
        }

        // List what's in the target root
        tracing::warn!("[KLEINIA-DEBUG] target root contents:");
        if let Ok(entries) = std::fs::read_dir(bootc_rootfs_mountpoint) {
            for e in entries.filter_map(|e| e.ok()) {
                tracing::warn!("[KLEINIA-DEBUG]   {:?} (dir={})", e.file_name(), e.file_type().map(|t| t.is_dir()).unwrap_or(false));
            }
        }
        tracing::warn!("[KLEINIA-DEBUG] df of /var/tmp: {:?}", std::process::Command::new("df").arg("-h").arg("/var/tmp").output().map(|o| String::from_utf8_lossy(&o.stdout).to_string()));

        tracing::warn!("[KLEINIA-DEBUG] calling bootc_copy now...");
                // Self-bind non-mountpoint dirs (bootc requires only mount points)
        tracing::warn!("[KLEINIA-DEBUG] self-binding non-mountpoint dirs...");
        if let Ok(entries) = std::fs::read_dir(bootc_rootfs_mountpoint) {
            for entry in entries.filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.is_dir() {
                    let path_str = path.to_str().unwrap_or_default();
                    let _ = std::process::Command::new("mount")
                        .args(["--bind", path_str, path_str])
                        .status();
                }
            }
        }

self.bootc_copy(bootc_rootfs_mountpoint, generate_cryptdata(mounts)?)?;
        tracing::warn!("[KLEINIA-DEBUG] bootc_copy returned OK");

        // Undo /var/tmp redirect
        tracing::warn!("[KLEINIA-DEBUG] undoing var/tmp redirect");
        let _ = std::process::Command::new("umount")
            .arg("/var/tmp")
            .status();

        tracing::warn!("[KLEINIA-DEBUG] unmounting all");
        if let Err(e) = mounts.umount_all(bootc_rootfs_mountpoint) {
            tracing::warn!("[KLEINIA-DEBUG] umount_all failed: {:?}, using lazy umount", e);
            let root_str = bootc_rootfs_mountpoint.to_str().unwrap_or_default();
            let _ = std::process::Command::new("umount")
                .args(["-R", "-l", root_str])
                .status();
        }
        tracing::warn!("[KLEINIA-DEBUG] run() complete");
        Ok(())
    }

    fn cleanup(&self, playbook: &crate::playbook::Playbook, mounts: &Mounts) -> Result<()> {
        let tmproot = tempfile::tempdir()?;
        let bootc_rootfs_mountpoint = tmproot.path();
        let mut sorted_mounts = mounts.clone();
        sorted_mounts.sort_mounts();
        sorted_mounts.mount_all(
            bootc_rootfs_mountpoint,
            playbook
                .encryption
                .as_ref()
                .map(|e| e.encryption_key.as_str()),
        )?;
        Self::bootc_cleanup(bootc_rootfs_mountpoint)?;
        crate::cmd!("sync" => |_| bail!("`sync` failed"));
        crate::cmd!("umount" [["-R"], [bootc_rootfs_mountpoint]] => |_| bail!("umount -R {bootc_rootfs_mountpoint:?} failed"));
        Ok(())
    }
}
