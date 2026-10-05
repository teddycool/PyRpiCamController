#!/usr/bin/env python3
"""Provision an admin-created logging key without sending it in process arguments."""

import argparse
import getpass
import sys
from secure_enroll_device import (
    setup_ssh_session,
    close_ssh_session,
    push_logging_key_to_pi,
    configure_remote_logging,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--ssh-user", required=True)
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--ssh-key")
    parser.add_argument("--backend-url", required=True, help="HTTPS backend base URL")
    args = parser.parse_args()
    key = getpass.getpass("New logging key (hidden): ")
    try:
        setup_ssh_session(args.host, args.ssh_user, args.ssh_port, args.ssh_key)
        push_logging_key_to_pi(args.host, args.ssh_user, args.ssh_port, key)
        configure_remote_logging(args.host, args.ssh_user, args.ssh_port, args.backend_url)
        print("Logging credential provisioned; camera service restarted.")
        return 0
    except Exception:
        print(
            "Provisioning failed. Check SSH access, sudo permissions and HTTPS backend URL.",
            file=sys.stderr,
        )
        return 1
    finally:
        close_ssh_session(args.host, args.ssh_user, args.ssh_port)


if __name__ == "__main__":
    raise SystemExit(main())
