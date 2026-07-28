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
from pathlib import Path


class ProvisioningError(Exception):
    """Base exception for provisioning errors."""
    pass


class ProvisioningManager:
    """Orchestrates provisioning of a fresh Pi."""

    def __init__(self, pi_ip, pi_user, release_version, device_name, location,
                 backend_url=None, non_interactive=False, skip_hwconfig=False,
                 skip_enrollment=False, ssh_timeout=60):
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

        # Derive tarball filename and GitHub URL
        self.tarball_filename = f"PyRpiCamController-{self.release_version}.tar.gz"
        self.tarball_url = (
            f"https://github.com/teddycool/PyRpiCamController/releases/"
            f"download/{self.release_tag}/{self.tarball_filename}"
        )
        self.repo_dir = Path(__file__).parent.parent

    @staticmethod
    def _normalize_version(version_str):
        """Normalize version string (add 'v' prefix if missing)."""
        if not version_str.startswith('v'):
            return f"v{version_str}"
        return version_str

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
        ssh_cmd = [
            "ssh",
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "SendEnv=none",
            f"{self.pi_user}@{self.pi_ip}",
        ]

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

    def verify_pi_connectivity(self):
        """Verify SSH connectivity to Pi."""
        print("\n[0/5] Verifying Pi connectivity...")
        try:
            result = self.ssh_run(
                "echo 'SSH connectivity verified'",
                "Testing SSH connection",
                check=True
            )
        except ProvisioningError as e:
            raise ProvisioningError(
                f"Cannot connect to Pi at {self.pi_ip}. Make sure:\n"
                f"  - Pi is powered on and has IP {self.pi_ip}\n"
                f"  - SSH is enabled (usually enabled by default on Pi OS)\n"
                f"  - Your SSH key is authorized (or password is configured)\n"
                f"\nDetails: {e}"
            )

    def download_and_extract(self):
        """Download and extract release tarball on Pi."""
        print("\n[1/5] Downloading and extracting release {}...".format(self.release_tag))

        commands = [
            "command -v wget >/dev/null 2>&1 || command -v curl >/dev/null 2>&1",
            (
                f"cd ~ && rm -rf PyRpiCamController && "
                f"(wget --quiet {self.tarball_url} -O {self.tarball_filename} "
                f"|| curl -fsSL {self.tarball_url} -o {self.tarball_filename})"
            ),
            f"cd ~ && tar -xzf {self.tarball_filename}",
            f"rm ~/{self.tarball_filename}",
            "ls -ld ~/PyRpiCamController && echo 'Extraction verified'",
        ]

        for cmd in commands:
            self.ssh_run(cmd, check=True)

        print("  ✓ Release extracted to ~/PyRpiCamController")

    def run_installer(self):
        """Run installer on Pi."""
        print("\n[2/5] Running installation script...")

        installer_args = ["python3", "tools/install-all-optimized.py"]

        if self.skip_hwconfig:
            installer_args.append("--skip-hwconfig")
        elif self.non_interactive:
            installer_args.append("--non-interactive")

        cmd = f"cd ~/PyRpiCamController && {' '.join(installer_args)}"

        # Note: installer may take 5-10 minutes
        print("  (This may take 5-10 minutes, please wait...)\n")
        self.ssh_run(cmd, "Running install-all-optimized.py", check=True)

        print("\n  ✓ Installation complete")

    def enroll_device(self):
        """Enroll device from dev machine."""
        print("\n[3/5] Enrolling device with backend...")

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
        print("\n[4/5] Verifying installation...")

        checks = [
            ("sudo systemctl is-active --quiet camcontroller", "Camera controller service"),
            ("sudo systemctl is-active --quiet camcontroller-update", "OTA update daemon"),
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

    def print_summary(self):
        """Print provisioning summary."""
        print("\n" + "=" * 60)
        print("✅ PROVISIONING COMPLETE")
        print("=" * 60)
        print(f"\nDevice:        {self.device_name}")
        print(f"Location:      {self.location}")
        print(f"IP Address:    {self.pi_ip}")
        print(f"Release:       {self.release_tag}")
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
            print(f"Release:  {self.release_tag}")
            print(f"Device:   {self.device_name}")
            print(f"Location: {self.location}")
            print("=" * 60)

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
    )

    return manager.provision()


if __name__ == "__main__":
    sys.exit(main())
