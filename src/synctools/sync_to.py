#!/usr/bin/env python3
"""
sync_to - Synchronize current directory TO a remote parent directory

Usage: sync_to <remote_parent_dir>

This script synchronizes the current working directory TO a subdirectory
of the remote parent directory. The subdirectory will have the same name
as the current working directory's basename.

Example:
  cd /home/user/myproject
  sync_to /backup
  # Syncs FROM /home/user/myproject TO /backup/myproject
"""

import sys
from pathlib import Path

# Import from the same package
from .sync_dirs import (
    validate_directory,
    check_rsync_available,
    sync_directories,
)


def main():
    """Main function for sync_to command."""
    # Check for correct number of arguments
    if len(sys.argv) != 2:
        print("Usage: sync_to <remote_parent_dir>", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Synchronizes current directory TO <remote_parent_dir>/$(basename $PWD)",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  cd /home/user/myproject", file=sys.stderr)
        print("  sync_to /backup", file=sys.stderr)
        print("  # Syncs FROM current directory TO /backup/myproject", file=sys.stderr)
        sys.exit(1)

    remote_parent_path = sys.argv[1]
    current_dir = Path.cwd()

    # Check if rsync is available
    if not check_rsync_available():
        print("Error: rsync is not available on this system.", file=sys.stderr)
        print("Please install rsync:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt-get install rsync", file=sys.stderr)
        print("  macOS: brew install rsync (or use built-in version)", file=sys.stderr)
        print("  Windows: Install via WSL, Cygwin, or msys2", file=sys.stderr)
        sys.exit(1)

    # Validate remote parent directory
    remote_parent = validate_directory(remote_parent_path, "Remote parent directory")

    print(f"Synchronizing FROM: {current_dir.resolve()}", file=sys.stderr)
    print(
        f"              TO: {remote_parent.resolve()}/{current_dir.name}",
        file=sys.stderr,
    )
    print("", file=sys.stderr)

    # Perform synchronization: source is current directory, destination is remote parent
    sync_directories(current_dir, remote_parent)


if __name__ == "__main__":
    main()
