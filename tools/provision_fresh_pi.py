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
"""

import argparse
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

    def __init__(self, pi_ip, pi_user, release_version, device_name, location,
                 backend_url=None, non_interactive=False, skip_hwconfig=False,
                 skip_enrollment=False, ssh_timeout=60, local=False,
                 install_timeout=1800):
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
        print("[0/5] Opening SSH session (you may be prompted for password once)...")
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
        )
        if result.returncode != 0:
            raise ProvisioningError(
                f"Cannot connect to Pi at {self.pi_ip}. Make sure:\n"
                f"  - Pi is powered on and reachable at {self.pi_ip}\n"
                f"  - SSH is enabled on the Pi\n"
                f"  - SSH credentials are correct"
            )

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
            f"cd ~ && rm -rf PyRpiCamController && "
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

        self.ssh_run(
            f"cd ~ && rm -rf PyRpiCamController && tar -xzf {self.tarball_filename} && rm {self.tarball_filename}",
            "Extracting",
            check=True,
        )
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

        print("\n  ✓ Installation complete")

    def enroll_device(self):
        """Enroll device from dev machine."""
        print("\n[4/5] Enrolling device with backend...")

        if not (self.repo_dir / "tools" / "secure_enroll_device.py").exists():
            raise ProvisioningError(
                "secure_enroll_device.py not found in tools/ directory"
            )

        enroll_cmd = [
            sys.executable,
            str(self.repo_dir / "tools" / "secure_enroll_device.py"),
            "--host", self.pi_ip,
            "--name", self.device_name,
            "--location", self.location,
        ]

        if self.backend_url:
            enroll_cmd.extend(["--backend-url", self.backend_url])

        try:
            subprocess.run(enroll_cmd, check=True, timeout=120)
            print("\n  ✓ Device enrollment successful")
        except subprocess.CalledProcessError as e:
            raise ProvisioningError(
                f"Device enrollment failed: {e}"
            )
        except subprocess.TimeoutExpired:
            raise ProvisioningError(
                "Device enrollment timed out (120s)"
            )

    def verify_installation(self):
        """Verify installation success."""
        print("\n[5/5] Verifying installation...")

        self.wait_for_service_active("camcontroller.service", "Camera controller service")
        self.wait_for_service_active("camcontroller-update.service", "OTA update daemon")

        checks = [
            ("[[ -f ~/PyRpiCamController/CamController/hwconfig.py ]]", "Hardware config file"),
            (f"[[ -f /home/{self.pi_user}/.camcontroller_ota ]]", "OTA settings file"),
        ]

        for cmd, description in checks:
            # Suppress stderr for cleaner output
            self.ssh_run(
                f"{cmd} 2>/dev/null",
                description,
                check=True
            )

        print("\n  ✓ All verification checks passed")

    def wait_for_service_active(self, service_name, label, timeout=180, interval=5):
        """Wait for a systemd service to become active with retries."""
        print(f"  → {label}...", end=" ", flush=True)
        deadline = time.time() + timeout
        last_state = "unknown"

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
        print("\nNext Steps:")
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

            self.open_ssh_session()
            self.verify_pi_connectivity()
            self.download_and_extract()
            self.run_installer()

            if not self.skip_enrollment:
                self.enroll_device()

            self.verify_installation()
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

    args = parser.parse_args()

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
    )

    return manager.provision()


if __name__ == "__main__":
    sys.exit(main())
