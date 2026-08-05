#!/usr/bin/env python3
"""
Provision a fresh Raspberry Pi from a GitHub release tarball.

This script handles the complete setup of a new Pi:
1. Download & extract release tarball via SSH
2. Run the installer (non-interactive or with prompts)
3. Enroll the device with the backend
4. Verify installation

Usage:
    python3 provision_fresh_pi.py <pi_ip> <release_version> <device_name> <location> [options]

Examples:
    # Non-interactive (uses defaults for hwconfig)
    python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-01" "Entryway" --non-interactive

    # Interactive (prompts for camera, display, features)
    python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-02" "Hallway"

    # Custom admin backend URL
    python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-03" "Kitchen" \\
        --backend-url https://admin.myserver.com --non-interactive
        
    python3 tools/provision_fresh_pi.py 192.168.199 1.3.0 "RpiCam1" "BeeHive1"

"""

import argparse
import getpass
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class ProvisioningError(Exception):
    """Base exception for provisioning errors."""
    pass


class ProvisioningManager:
    """Orchestrates provisioning of a fresh Pi."""

    CACHE_FILE = Path.home() / ".provision_cache.json"

    def __init__(self, pi_ip, pi_user, release_version, device_name, location,
                 backend_url=None, non_interactive=False, skip_hwconfig=False,
                 skip_enrollment=False, ssh_timeout=60, local=False,
                 install_timeout=1800, ssh_posture="keep", ssh_pubkey=None,
                 lock_password=True, use_cached_password=False, cache_password=False,
                 production=False):
        """
        Initialize provisioning manager.

        Args:
            pi_ip: IP address of the Pi
            pi_user: SSH user (default: 'pi')
            release_version: GitHub release tag (e.g., 'v1.0.0' or '1.0.0')
            device_name: Human-readable device name
            location: Physical location description
            backend_url: Optional backend URL override
            non_interactive: Skip hwconfig prompts, use defaults
            skip_hwconfig: Don't run hwconfig configuration
            skip_enrollment: Don't run device enrollment
            ssh_timeout: SSH command timeout in seconds
            local: Build tarball from local repo instead of downloading from GitHub
            install_timeout: Seconds before installer is considered hung (default 1800 = 30 min)
            ssh_posture: Post-provision SSH posture: keep, key-only, or disable
            ssh_pubkey: Optional path to local public key to install on Pi
            lock_password: Lock the Pi user's password after provisioning
        """
        self.pi_ip = pi_ip
        self.pi_user = pi_user
        self.release_tag = self._normalize_version(release_version)
        self.release_version = self.release_tag.removeprefix("v")
        self.device_name = device_name
        self.location = location
        self.backend_url = backend_url
        self.non_interactive = non_interactive
        self.skip_hwconfig = skip_hwconfig
        self.skip_enrollment = skip_enrollment
        self.ssh_timeout = ssh_timeout
        self.local = local
        self.install_timeout = install_timeout
        self.ssh_posture = ssh_posture
        self.ssh_pubkey = Path(ssh_pubkey).expanduser() if ssh_pubkey else None
        self.lock_password = lock_password
        self.use_cached_password = use_cached_password
        self.cache_password = cache_password
        self.production = production
        self.final_ssh_posture = "unchanged"
        self.password_locked = False

        # Derive tarball filename and GitHub URL
        self.tarball_filename = f"PyRpiCamController-{self.release_version}.tar.gz"
        self.tarball_url = (
            f"https://github.com/teddycool/PyRpiCamController/releases/"
            f"download/{self.release_tag}/{self.tarball_filename}"
        )
        self.repo_dir = Path(__file__).parent.parent
        self._ctl_socket = None

    @staticmethod
    def _normalize_version(version_str):
        """Normalize version string (add 'v' prefix if missing)."""
        if not version_str.startswith('v'):
            return f"v{version_str}"
        return version_str

    def _get_cached_password(self):
        """
        Retrieve cached password for this Pi from local cache file.
        Returns None if no cached password exists for this host.
        """
        if not self.CACHE_FILE.exists():
            return None
        try:
            cache = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
            host_key = f"{self.pi_user}@{self.pi_ip}"
            return cache.get(host_key)
        except (json.JSONDecodeError, OSError):
            return None

    def _save_password_to_cache(self, password):
        """Save password to local cache file for future use."""
        try:
            cache = {}
            if self.CACHE_FILE.exists():
                cache = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}

        host_key = f"{self.pi_user}@{self.pi_ip}"
        cache[host_key] = password
        
        try:
            self.CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            self.CACHE_FILE.chmod(0o600)  # readable/writable only by owner
            print(f"  ℹ  Password cached for future use (~/.provision_cache.json)")
        except OSError as e:
            print(f"  ⚠  Could not cache password: {e}")

    def _clear_cached_password(self):
        """Remove cached password for this Pi from cache file."""
        if not self.CACHE_FILE.exists():
            return
        try:
            cache = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
            host_key = f"{self.pi_user}@{self.pi_ip}"
            if host_key in cache:
                del cache[host_key]
                self.CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
                self.CACHE_FILE.chmod(0o600)
        except (json.JSONDecodeError, OSError):
            pass

    def _base_ssh_opts(self):
        """Return base SSH options, using ControlMaster socket when available."""
        opts = [
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "SendEnv=none",
        ]
        if self._ctl_socket:
            opts += ["-o", "ControlMaster=no", "-o", f"ControlPath={self._ctl_socket}"]
        return opts

    def open_ssh_session(self):
        """Open a persistent SSH ControlMaster session (single password prompt)."""
        self._ctl_socket = tempfile.mktemp(prefix="prov_ssh_", suffix=".ctl")
        
        cached_password = None
        if self.use_cached_password:
            cached_password = self._get_cached_password()
            if cached_password:
                print("[0/5] Opening SSH session (using cached password)...")
            else:
                print("[0/5] Opening SSH session (no cached password found; you may be prompted)...")
        else:
            print("[0/5] Opening SSH session (you may be prompted for password once)...")
        
        env = os.environ.copy()
        askpass_script = None
        
        # If we have a cached password, use SSH_ASKPASS to provide it programmatically
        if cached_password:
            askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
            askpass_script.write(f"#!/bin/sh\necho '{shlex.quote(cached_password)}'\n")
            askpass_script.close()
            os.chmod(askpass_script.name, 0o700)
            env["SSH_ASKPASS"] = askpass_script.name
            env["SSH_ASKPASS_REQUIRE"] = "force"
            env["DISPLAY"] = ":0"  # Required for SSH_ASKPASS to work
        
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "ConnectTimeout=10",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "SendEnv=none",
                    "-o", "ControlMaster=yes",
                    "-o", f"ControlPath={self._ctl_socket}",
                    "-o", "ControlPersist=600",
                    "-f",   # fork into background after auth
                    "-N",   # no remote command
                    f"{self.pi_user}@{self.pi_ip}",
                ],
                env=env,
            )
            if result.returncode != 0:
                # If cached password failed, clear it and raise error
                if cached_password:
                    print("  ⚠  Cached password failed; clearing cache")
                    self._clear_cached_password()
                raise ProvisioningError(
                    f"Cannot connect to Pi at {self.pi_ip}. Make sure:\n"
                    f"  - Pi is powered on and reachable at {self.pi_ip}\n"
                    f"  - SSH is enabled on the Pi\n"
                    f"  - SSH credentials are correct"
                )
            
            # If we successfully used a cached password, note it
            if cached_password:
                print("  ✓ Using cached credentials")
        
        finally:
            # Clean up SSH_ASKPASS script
            if askpass_script:
                try:
                    os.unlink(askpass_script.name)
                except OSError:
                    pass

    def close_ssh_session(self):
        """Close the ControlMaster session."""
        if self._ctl_socket:
            subprocess.run(
                ["ssh", "-o", f"ControlPath={self._ctl_socket}", "-O", "exit",
                 f"{self.pi_user}@{self.pi_ip}"],
                capture_output=True,
            )
            self._ctl_socket = None

    def ssh_run(self, command, description=None, check=True):
        """
        Execute command on Pi via SSH.

        Args:
            command: Shell command to run
            description: Human-readable description for logging
            check: Raise exception on non-zero exit

        Returns:
            Completed process object
        """
        ssh_cmd = ["ssh"] + self._base_ssh_opts() + [f"{self.pi_user}@{self.pi_ip}"]

        if description:
            print(f"  → {description}...", end=" ", flush=True)

        try:
            result = subprocess.run(
                ssh_cmd + [command],
                capture_output=True,
                text=True,
                timeout=self.ssh_timeout,
                check=False
            )

            if check and result.returncode != 0:
                print("✗")
                raise ProvisioningError(
                    f"SSH command failed ({result.returncode}):\n"
                    f"  Command: {command}\n"
                    f"  Stderr: {result.stderr}"
                )

            if description:
                print("✓")
            return result

        except subprocess.TimeoutExpired:
            print("✗")
            raise ProvisioningError(
                f"SSH command timed out after {self.ssh_timeout}s: {command}"
            )
        except Exception as e:
            print(f"✗ ({e})")
            raise

    def ssh_stream(self, command, timeout=1800):
        """
        Execute a long-running command on the Pi and stream output live to the
        terminal. No capture — output flows directly to stdout/stderr.

        Args:
            command: Shell command to run
            timeout: Timeout in seconds (default 1800 = 30 minutes)
        """
        ssh_cmd = ["ssh"] + self._base_ssh_opts() + ["-t", f"{self.pi_user}@{self.pi_ip}"]
        try:
            result = subprocess.run(
                ssh_cmd + [command],
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise ProvisioningError(
                f"Command timed out after {timeout}s ({timeout//60} min).\n"
                f"  Command: {command}"
            )
        if result.returncode != 0:
            raise ProvisioningError(
                f"Command failed (exit {result.returncode}):\n  {command}"
            )

    def scp_run(self, local_path, remote_path):
        """Copy a file to the Pi via SCP using the existing ControlMaster socket."""
        scp_cmd = ["scp"] + self._base_ssh_opts() + [str(local_path), f"{self.pi_user}@{self.pi_ip}:{remote_path}"]
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise ProvisioningError(f"SCP failed: {result.stderr}")

    def pull_file(self, remote_path, local_path):
        """Copy a file from the Pi to local filesystem via SCP."""
        scp_cmd = ["scp"] + self._base_ssh_opts() + [f"{self.pi_user}@{self.pi_ip}:{remote_path}", str(local_path)]
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise ProvisioningError(f"SCP pull failed: {result.stderr}")

    def _build_local_tarball(self, out_path: Path):
        """Produce a tar.gz build artifact into out_path (git archive HEAD)."""
        result = subprocess.run(
            [
                "git", "archive",
                "--format=tar.gz",
                f"--output={out_path}",
                "--prefix=PyRpiCamController/",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            cwd=self.repo_dir,
        )
        if result.returncode != 0:
            raise ProvisioningError(f"git archive failed: {result.stderr}")

    def _sha256_of(self, path: Path):
        import hashlib
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _try_smbclient_upload(self, device_dir_name, local_files):
        """Attempt to upload files using smbclient with current local username."""
        smbshare = "//192.168.1.104/backup"
        smb_user = getpass.getuser()

        # create remote dirs (pyrpicam and device subdir)
        mk_cmds = [f"mkdir pyrpicam", f"mkdir pyrpicam/{device_dir_name}"]
        mk_cmd = "; ".join(mk_cmds)
        mk_full = ["smbclient", smbshare, "-U", smb_user, "-c", mk_cmd]
        try:
            mk_result = subprocess.run(mk_full, timeout=30)
            if mk_result.returncode != 0:
                return False
        except Exception:
            return False

        # put files
        put_cmds = [f"cd pyrpicam/{device_dir_name}"]
        for p in local_files:
            put_cmds.append(f"lcd {shlex.quote(str(p.parent))}")
            put_cmds.append(f"put {shlex.quote(p.name)}")
        put_full = ["smbclient", smbshare, "-U", smb_user, "-c", "; ".join(put_cmds)]
        try:
            result = subprocess.run(put_full, timeout=120)
            return result.returncode == 0
        except Exception:
            return False

    def _try_mount_and_copy(self, device_dir_name, local_files):
        """Attempt to mount the cifs share (requires sudo) and copy files, then unmount."""
        mount_point = Path(tempfile.mkdtemp(prefix="pyrbackup_"))
        share = f"//192.168.1.104/backup"
        user = getpass.getuser()
        try:
            mount_cmd = [
                "sudo", "mount", "-t", "cifs", share, str(mount_point),
                "-o", f"username={user},rw,vers=3.0"
            ]
            r = subprocess.run(mount_cmd, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return False
            target = mount_point / "pyrpicam" / device_dir_name
            target.mkdir(parents=True, exist_ok=True)
            for p in local_files:
                dest = target / p.name
                subprocess.run(["/bin/cp", str(p), str(dest)], check=True)
            return True
        except Exception:
            return False
        finally:
            # try to unmount
            try:
                subprocess.run(["sudo", "umount", str(mount_point)], capture_output=True, timeout=10)
            except Exception:
                pass

    def store_production_artifacts(self):
        """Collect and store production artifacts on the backup SMB share.

        Artifacts saved per device into smb://192.168.1.104/backup/pyrpicam/<device-id>
        """
        # Use device hostname (derived from CPU ID by installer) as backup folder name.
        device_id = self.device_name.replace(" ", "_")
        try:
            host_res = self.ssh_run("hostname", check=False)
            host_name = (host_res.stdout or "").strip()
            if host_name:
                device_id = host_name
        except Exception:
            pass
        print(f"\n→ Storing production artifacts for {device_id}...")

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            local_files = []

            # 1) Device SMB credentials generated during install
            try:
                device_cred = tmp / "smb_credentials.txt"
                self.pull_file(f"~/shared/smb_credentials.txt", device_cred)
                local_files.append(device_cred)
            except Exception:
                # Keep a fallback note if device credential card is missing
                cred_file = tmp / "smb_credentials.txt"
                cred_file.write_text(
                    "device smb credentials file not found on device (/home/pi/shared/smb_credentials.txt)\n",
                    encoding="utf-8",
                )
                local_files.append(cred_file)

            # 2) Pull hwconfig from Pi (if present)
            try:
                hw_local = tmp / "hwconfig.py"
                self.pull_file(f"~/PyRpiCamController/CamController/hwconfig.py", hw_local)
                local_files.append(hw_local)
            except Exception:
                # fallback: copy default schema from repo if available
                schema = self.repo_dir / "Settings" / "settings_schema.json"
                if schema.exists():
                    dest = tmp / schema.name
                    subprocess.run(["/bin/cp", str(schema), str(dest)], check=False)
                    local_files.append(dest)

            # 2b) Pull deployed settings overrides (complete deployed settings file)
            try:
                settings_local = tmp / "user_settings.json"
                self.pull_file(f"~/PyRpiCamController/Settings/user_settings.json", settings_local)
                local_files.append(settings_local)
            except Exception:
                pass

            # 3) OTA api key (attempt to read via settings_manager)
            try:
                cmd = (
                    "cd ~/PyRpiCamController && "
                    "python3 -c \"from Settings.settings_manager import settings_manager as s; print(s.get('OTA.api_key') or '')\""
                )
                res = self.ssh_run(cmd, check=False)
                ota_key = (res.stdout or "").strip()
                ota_file = tmp / "ota_api_key.txt"
                ota_file.write_text(ota_key or "(not found)", encoding="utf-8")
                local_files.append(ota_file)
            except Exception:
                pass

            # 4) operator SSH public key
            pubkey = None
            if self.ssh_pubkey and Path(self.ssh_pubkey).exists():
                pubkey = Path(self.ssh_pubkey)
            else:
                # common default
                for cand in [Path.home() / ".ssh" / "id_ed25519.pub", Path.home() / ".ssh" / "id_rsa.pub"]:
                    if cand.exists():
                        pubkey = cand
                        break
            if pubkey:
                dest = tmp / pubkey.name
                subprocess.run(["/bin/cp", str(pubkey), str(dest)], check=False)
                local_files.append(dest)

            # 5) Build artifact & sha256 (prefer dist/ artifact, else build)
            dist_artifact = self.repo_dir / "dist" / self.tarball_filename
            if dist_artifact.exists():
                dest = tmp / dist_artifact.name
                subprocess.run(["/bin/cp", str(dist_artifact), str(dest)], check=False)
            else:
                dest = tmp / self.tarball_filename
                try:
                    self._build_local_tarball(dest)
                except Exception:
                    dest = None
            if dest and dest.exists():
                local_files.append(dest)
                sha = self._sha256_of(dest)
                sha_file = tmp / (dest.name + ".sha256")
                sha_file.write_text(sha, encoding="utf-8")
                local_files.append(sha_file)

            # Try smbclient upload first
            if self._try_smbclient_upload(device_id, local_files):
                print("  ✓ Artifacts uploaded via smbclient")
                return

            # Try mount+copy (requires sudo on local machine and cifs-utils)
            if self._try_mount_and_copy(device_id, local_files):
                print("  ✓ Artifacts copied via temporary CIFS mount")
                return

            # Fallback: leave files locally and inform user
            fallback_dir = Path.home() / "pyrpicam_backup" / device_id
            fallback_dir.mkdir(parents=True, exist_ok=True)
            for p in local_files:
                try:
                    subprocess.run(["/bin/cp", str(p), str(fallback_dir / p.name)], check=False)
                except Exception:
                    pass
            print(f"  ⚠  Could not upload artifacts to SMB share. Local copies saved to: {fallback_dir}")

    def verify_pi_connectivity(self):
        """Verify SSH connectivity to Pi (ControlMaster already open)."""
        print("\n[1/5] Verifying Pi connectivity...")
        self.ssh_run("echo 'SSH ok'", "Testing SSH connection", check=True)

    def download_and_extract(self):
        """Download (or build locally and SCP) and extract release tarball on Pi."""
        if self.local:
            self._build_and_scp_local()
        else:
            self._download_from_github()

    def _download_from_github(self):
        """Download release tarball from GitHub and extract on Pi."""
        print("\n[2/5] Downloading release {} from GitHub...".format(self.release_tag))
        self.ssh_run(
            f"sudo rm -rf /home/{self.pi_user}/PyRpiCamController && "
            f"sudo chown -R {self.pi_user}:{self.pi_user} /home/{self.pi_user}",
            "Cleaning previous deployment",
            check=True,
        )
        self.ssh_run(
            f"(wget --quiet {self.tarball_url} -O {self.tarball_filename} "
            f"|| curl -fsSL {self.tarball_url} -o {self.tarball_filename})",
            "Downloading tarball",
            check=True,
        )
        self.ssh_run(f"cd ~ && tar -xzf {self.tarball_filename} && rm {self.tarball_filename}",
                     "Extracting", check=True)
        print("  ✓ Release extracted to ~/PyRpiCamController")

    def _build_and_scp_local(self):
        """Build tarball from local repo and SCP it to the Pi."""
        print("\n[2/5] Building tarball from local repo and copying to Pi...")
        self.ssh_run(
            f"sudo rm -rf /home/{self.pi_user}/PyRpiCamController && "
            f"sudo chown -R {self.pi_user}:{self.pi_user} /home/{self.pi_user}",
            "Cleaning previous deployment",
            check=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = Path(tmpdir) / self.tarball_filename
            print(f"  → Building {self.tarball_filename}...", end=" ", flush=True)
            result = subprocess.run(
                [
                    "git", "archive",
                    "--format=tar.gz",
                    "--prefix=PyRpiCamController/",
                    f"--output={tarball_path}",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                cwd=self.repo_dir,
            )
            if result.returncode != 0:
                print("✗")
                raise ProvisioningError(f"git archive failed: {result.stderr}")
            print("✓")

            print(f"  → Copying to Pi...", end=" ", flush=True)
            self.scp_run(tarball_path, f"~/{self.tarball_filename}")
            print("✓")

        self.ssh_run(f"cd ~ && tar -xzf {self.tarball_filename} && rm {self.tarball_filename}", "Extracting", check=True)
        print("  ✓ Local build extracted to ~/PyRpiCamController")

    def run_installer(self):
        """Run installer on Pi."""
        print("\n[3/5] Running installation script...")

        installer_args = ["python3", "tools/install-all-optimized.py"]

        if self.skip_hwconfig:
            installer_args.append("--skip-hwconfig")
        elif self.non_interactive:
            installer_args.append("--non-interactive")

        cmd = f"cd ~/PyRpiCamController && {' '.join(installer_args)}"

        print("  (Output streamed live — this can take 15–20 min on a Pi 3)\n")
        self.ssh_stream(cmd, timeout=self.install_timeout)

        self.ensure_services_started()

        print("\n  ✓ Installation complete")

    def ensure_services_started(self):
        """Reload units and start core services after installation."""
        print("\n  → Ensuring services are started...", end=" ", flush=True)
        self.ssh_run(
            f"sudo mkdir -p /home/{self.pi_user}/ota/commands /home/{self.pi_user}/shared/logs && "
            f"sudo chown -R {self.pi_user}:{self.pi_user} /home/{self.pi_user}/ota /home/{self.pi_user}/shared && "
            f"sudo chmod 775 /home/{self.pi_user}/ota/commands",
            check=True,
        )
        self.ssh_run("sudo systemctl daemon-reload", check=True)
        self.ssh_run(
            "sudo systemctl enable camcontroller.service camcontroller-update.service",
            check=True,
        )
        self.ssh_run(
            "sudo systemctl restart camcontroller.service camcontroller-update.service",
            check=True,
        )
        print("✓")

    def _install_pubkey_on_pi(self):
        """Install the operator SSH public key on the Pi (idempotent)."""
        if not self.ssh_pubkey:
            return
        if not self.ssh_pubkey.exists():
            raise ProvisioningError(f"SSH public key file not found: {self.ssh_pubkey}")
        pubkey_text = self.ssh_pubkey.read_text(encoding="utf-8").strip()
        if not pubkey_text.startswith("ssh-"):
            raise ProvisioningError(f"Invalid SSH public key format in: {self.ssh_pubkey}")
        quoted_key = shlex.quote(pubkey_text)
        self.ssh_run(
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
            "touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && "
            f"grep -qxF {quoted_key} ~/.ssh/authorized_keys || echo {quoted_key} >> ~/.ssh/authorized_keys",
            "Installing operator SSH public key (pre-enrollment)",
            check=True,
        )

    def enroll_device(self):
        """Enroll device from dev machine."""
        print("\n[4/5] Enrolling device with backend...")

        if not (self.repo_dir / "tools" / "secure_enroll_device.py").exists():
            raise ProvisioningError(
                "secure_enroll_device.py not found in tools/ directory"
            )

        # Install SSH key before enrollment so the subprocess can use it
        # without an interactive password prompt.
        self._install_pubkey_on_pi()

        enroll_cmd = [
            sys.executable,
            str(self.repo_dir / "tools" / "secure_enroll_device.py"),
            "--host", self.pi_ip,
            "--name", self.device_name,
            "--location", self.location,
        ]

        # Pass private key derived from --ssh-pubkey (strip .pub suffix)
        if self.ssh_pubkey:
            privkey = Path(str(self.ssh_pubkey).removesuffix(".pub"))
            if privkey.exists():
                enroll_cmd.extend(["--ssh-key", str(privkey)])

        if self.backend_url:
            enroll_cmd.extend(["--backend-url", self.backend_url])

        try:
            subprocess.run(enroll_cmd, check=True, timeout=180)
            print("\n  ✓ Device enrollment successful")
        except subprocess.CalledProcessError as e:
            raise ProvisioningError(
                f"Device enrollment failed: {e}"
            )
        except subprocess.TimeoutExpired:
            raise ProvisioningError(
                "Device enrollment timed out (180s)"
            )

    def verify_installation(self):
        """Verify installation success."""
        print("\n[5/5] Verifying installation...")

        self.wait_for_service_active("camcontroller.service", "Camera controller service")
        self.wait_for_service_active("camcontroller-update.service", "OTA update daemon")

        checks = [
            ("[[ -f ~/PyRpiCamController/CamController/hwconfig.py ]]", "Hardware config file"),
            ("mkdir -p ~/shared/logs && [[ -w ~/shared/logs ]]", "Log directory writable"),
        ]

        for cmd, description in checks:
            # Suppress stderr for cleaner output
            self.ssh_run(
                f"{cmd} 2>/dev/null",
                description,
                check=True
            )

        self.verify_ota_settings()

        print("\n  ✓ All verification checks passed")

    def apply_post_provision_hardening(self):
        """Apply v1 security baseline controls after successful provisioning."""
        print("\n[6/6] Applying post-provision hardening...")

        # Key is already installed by _install_pubkey_on_pi() before enrollment;
        # idempotent call here is a no-op but ensures correctness if enrollment was skipped.
        self._install_pubkey_on_pi()

        if self.ssh_posture == "key-only":
            has_keys = self.ssh_run("test -s ~/.ssh/authorized_keys", check=False)
            if has_keys.returncode != 0:
                raise ProvisioningError(
                    "Cannot enforce key-only SSH: no authorized keys found on device. "
                    "Provide --ssh-pubkey or use --ssh-posture keep for this run."
                )
            self.ssh_run(
                "printf '%s\n' "
                "'PasswordAuthentication no' "
                "'KbdInteractiveAuthentication no' "
                "'ChallengeResponseAuthentication no' "
                "'PubkeyAuthentication yes' "
                "'PermitRootLogin no' "
                "| sudo tee /etc/ssh/sshd_config.d/99-camcontroller-security.conf >/dev/null",
                "Setting SSH to key-only auth",
                check=True,
            )
            self.ssh_run("sudo systemctl reload ssh || sudo systemctl reload sshd", check=True)
            self.final_ssh_posture = "key_only"
        elif self.ssh_posture == "disable":
            self.ssh_run(
                "sudo systemctl disable --now ssh || sudo systemctl disable --now sshd",
                "Disabling SSH service",
                check=True,
            )
            self.final_ssh_posture = "disabled"
        else:
            self.final_ssh_posture = "unchanged"

        if self.lock_password and self.ssh_posture in ("key-only", "disable"):
            self.ssh_run(
                f"sudo passwd -l {self.pi_user} >/dev/null 2>&1 || true",
                "Locking local account password",
                check=True,
            )
            self.password_locked = True

        print("  ✓ Hardening complete")

    def verify_ota_settings(self):
        """Validate that OTA settings were written into settings_manager."""
        ota_check_cmd = (
            "cd ~/PyRpiCamController && "
            "python3 -c \""
            "from Settings.settings_manager import settings_manager as s; "
            "import sys; "
            "ok = bool(s.get('OtaEnable')) and bool(s.get('OTA.server_url')) and bool(s.get('OTA.api_key')); "
            "print('OK: OTA settings present' if ok else 'ERROR: OTA settings missing/incomplete'); "
            "sys.exit(0 if ok else 2)"
            "\""
        )
        self.ssh_run(ota_check_cmd, "OTA settings in settings_manager", check=True)

    def wait_for_service_active(self, service_name, label, timeout=180, interval=5):
        """Wait for a systemd service to become active with retries."""
        print(f"  → {label}...", end=" ", flush=True)
        deadline = time.time() + timeout
        last_state = "unknown"
        healed_namespace = False

        while time.time() < deadline:
            result = self.ssh_run(
                f"sudo systemctl is-active {service_name} 2>/dev/null",
                check=False,
            )
            state = (result.stdout or "").strip()
            if state == "active":
                print("✓")
                return

            if state:
                last_state = state

            if (not healed_namespace) and service_name == "camcontroller-update.service":
                status_result = self.ssh_run(
                    f"sudo systemctl --no-pager --full status {service_name} || true",
                    check=False,
                )
                status_text = (status_result.stdout or "") + (status_result.stderr or "")
                if "status=226/NAMESPACE" in status_text or "Failed to set up mount namespacing" in status_text:
                    self.ssh_run(
                        f"sudo mkdir -p /home/{self.pi_user}/ota/commands /home/{self.pi_user}/shared/logs && "
                        f"sudo chown -R {self.pi_user}:{self.pi_user} /home/{self.pi_user}/ota /home/{self.pi_user}/shared && "
                        f"sudo chmod 755 /home/{self.pi_user}/ota && "
                        f"sudo chmod 775 /home/{self.pi_user}/ota/commands",
                        check=True,
                    )
                    self.ssh_run("sudo systemctl daemon-reload", check=True)
                    self.ssh_run(f"sudo systemctl restart {service_name}", check=True)
                    healed_namespace = True

            time.sleep(interval)

        print("✗")
        status_result = self.ssh_run(
            f"sudo systemctl --no-pager --full status {service_name} || true",
            check=False,
        )
        journal_result = self.ssh_run(
            f"sudo journalctl -u {service_name} -n 60 --no-pager || true",
            check=False,
        )

        raise ProvisioningError(
            f"{label} did not become active within {timeout}s (last state: {last_state}).\n"
            f"\nService status:\n{status_result.stdout}\n"
            f"\nRecent journal:\n{journal_result.stdout}"
        )

    def print_summary(self):
        """Print provisioning summary."""
        print("\n" + "=" * 60)
        print("✅ PROVISIONING COMPLETE")
        print("=" * 60)
        print(f"\nDevice:        {self.device_name}")
        print(f"Location:      {self.location}")
        print(f"IP Address:    {self.pi_ip}")
        print(f"Release:       {'local build' if self.local else self.release_tag}")
        print(f"Enrollment:    {'Skipped' if self.skip_enrollment else 'Complete'}")
        print(f"SSH posture:   {self.final_ssh_posture}")
        print(f"Password lock: {'Applied' if self.password_locked else 'Not applied'}")
        print("\nNext Steps:")
        if self.final_ssh_posture == "disabled":
            print("  1. SSH was disabled by policy; use local console for direct access")
        else:
            print("  1. Access the device via SSH:")
            print(f"     ssh {self.pi_user}@{self.pi_ip}")
        print("  2. View logs for the camera controller:")
        print("     sudo journalctl -u camcontroller -f")
        print("  3. Check OTA update status:")
        print("     sudo journalctl -u camcontroller-update -n 50")
        print("\nDevice is now ready for OTA updates.")
        print("=" * 60 + "\n")

    def provision(self):
        """Execute full provisioning workflow."""
        try:
            print("\n" + "=" * 60)
            print(f"PyRpiCamController Fresh Pi Provisioning")
            print("=" * 60)
            print(f"Target:   {self.pi_user}@{self.pi_ip}")
            print(f"Release:  {'local build' if self.local else self.release_tag}")
            print(f"Device:   {self.device_name}")
            print(f"Location: {self.location}")
            print("=" * 60)

            # If --cache-password is set, prompt for password now
            if self.cache_password:
                import getpass
                password = getpass.getpass(f"Enter SSH password for {self.pi_user}@{self.pi_ip}: ")
                self._save_password_to_cache(password)
                # Set use_cached_password to True so open_ssh_session uses the cached password
                self.use_cached_password = True

            self.open_ssh_session()
            self.verify_pi_connectivity()
            self.download_and_extract()
            self.run_installer()

            if not self.skip_enrollment:
                self.enroll_device()

            self.verify_installation()
            # If production mode requested, collect and store artifacts to SMB backup
            if self.production:
                try:
                    self.store_production_artifacts()
                except Exception as e:
                    print(f"  ⚠  Production artifact storage failed: {e}")
            self.apply_post_provision_hardening()
            self.print_summary()

            return 0

        except ProvisioningError as e:
            print(f"\n❌ PROVISIONING FAILED: {e}")
            return 1
        except KeyboardInterrupt:
            print("\n\n⚠️  Provisioning interrupted by user")
            return 130
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}")
            return 1
        finally:
            self.close_ssh_session()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Provision a fresh Raspberry Pi from a GitHub release",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Non-interactive (quick, uses defaults)
  python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-01" "Entryway" --non-interactive

  # Interactive (prompts for camera, display, features)
  python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-02" "Hallway"

  # Custom admin backend
  python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-03" "Kitchen" \\
      --backend-url https://admin.example.com --non-interactive

    # Use local repo instead of GitHub release (no tag needed)
  python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-04" "Garage" \\
      --local --non-interactive

  # Reuse an existing hwconfig.py during install
  python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-04" "Garage" \\
      --skip-hwconfig --non-interactive

    # Production hardening: install key and disable password SSH
    python3 provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-Prod" "Warehouse" \
            --non-interactive --ssh-pubkey ~/.ssh/id_ed25519.pub --ssh-posture key-only
        """
    )

    parser.add_argument("pi_ip", help="IP address of the Pi")
    parser.add_argument("release_version", help="Release version (e.g., '1.0.0' or 'v1.0.0')")
    parser.add_argument("device_name", help="Human-readable device name")
    parser.add_argument("location", help="Physical location of the device")

    parser.add_argument(
        "--pi-user", default="pi",
        help="SSH user on Pi (default: pi)"
    )
    parser.add_argument(
        "--backend-url",
        help="Override backend URL (default: from hwconfig.py)"
    )
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Non-interactive mode (use defaults for hwconfig)"
    )
    parser.add_argument(
        "--skip-hwconfig", action="store_true",
        help="Skip hwconfig generation (use existing hwconfig.py)"
    )
    parser.add_argument(
        "--skip-enrollment", action="store_true",
        help="Skip device enrollment (manual enrollment later)"
    )
    parser.add_argument(
        "--ssh-timeout", type=int, default=60,
        help="SSH command timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--install-timeout", type=int, default=1800,
        help="Timeout in seconds for the install step (default: 1800 = 30 min)"
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Build tarball from local repo (git archive HEAD) and SCP to Pi instead of downloading from GitHub. "
             "Use when no GitHub release exists yet (e.g., during development)."
    )
    parser.add_argument(
        "--ssh-posture",
        choices=["keep", "key-only", "disable"],
        default="keep",
        help="Post-provision SSH posture (default: keep). Use key-only or disable for production hardening."
    )
    parser.add_argument(
        "--ssh-pubkey",
        help="Path to a local SSH public key to install on the Pi before enforcing SSH posture"
    )
    parser.add_argument(
        "--no-lock-password",
        action="store_true",
        help="Do not lock the Pi user's password when SSH posture is key-only or disable"
    )
    parser.add_argument(
        "--cache-password",
        action="store_true",
        help="Prompt for SSH password and cache it for future provisioning runs (~/.provision_cache.json)"
    )
    parser.add_argument(
        "--use-cached-password",
        action="store_true",
        help="Use cached SSH password from ~/.provision_cache.json for this host (if available)"
    )
    parser.add_argument(
        "--clear-password-cache",
        action="store_true",
        help="Clear cached password for this host and exit"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Enable production policy checks (requires hardened SSH posture and password lock)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate CLI arguments and policy checks, then exit without provisioning"
    )

    args = parser.parse_args()

    if args.production:
        if args.ssh_posture == "keep":
            parser.error(
                "--production requires --ssh-posture key-only or --ssh-posture disable"
            )
        if args.no_lock_password:
            parser.error(
                "--production does not allow --no-lock-password"
            )

    if args.validate_only:
        print("Argument and policy validation successful")
        return 0

    # Handle password cache clear operation
    if args.clear_password_cache:
        manager = ProvisioningManager(
            pi_ip=args.pi_ip,
            pi_user=args.pi_user,
            release_version=args.release_version,
            device_name=args.device_name,
            location=args.location,
        )
        manager._clear_cached_password()
        print(f"Cleared cached password for {args.pi_user}@{args.pi_ip}")
        return 0

    manager = ProvisioningManager(
        pi_ip=args.pi_ip,
        pi_user=args.pi_user,
        release_version=args.release_version,
        device_name=args.device_name,
        location=args.location,
        backend_url=args.backend_url,
        non_interactive=args.non_interactive,
        skip_hwconfig=args.skip_hwconfig,
        skip_enrollment=args.skip_enrollment,
        ssh_timeout=args.ssh_timeout,
        local=args.local,
        install_timeout=args.install_timeout,
        ssh_posture=args.ssh_posture,
        ssh_pubkey=args.ssh_pubkey,
        lock_password=not args.no_lock_password,
        use_cached_password=args.use_cached_password,
        cache_password=args.cache_password,
        production=args.production,
    )

    return manager.provision()


if __name__ == "__main__":
    sys.exit(main())
