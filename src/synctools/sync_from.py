#!/usr/bin/env python3
"""
sync_from - Synchronize current directory FROM a remote parent directory

Usage: sync_from <remote_parent_dir>

This script synchronizes the current working directory FROM a subdirectory
of the remote parent directory. The subdirectory must have the same name
as the current working directory's basename.

Example:
  cd /home/user/myproject
  sync_from /backup
  # Syncs FROM /backup/myproject TO /home/user/myproject
"""

import os
import sys
from pathlib import Path

# Import from the same package
from .sync_dirs import (
    validate_directory,
    check_rsync_available,
    sync_directories,
)


def main():
    """Main function for sync_from command."""
    # Check for correct number of arguments
    if len(sys.argv) != 2:
        print("Usage: sync_from <remote_parent_dir>", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Synchronizes current directory FROM <remote_parent_dir>/$(basename $PWD)",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  cd /home/user/myproject", file=sys.stderr)
        print("  sync_from /backup", file=sys.stderr)
        print("  # Syncs FROM /backup/myproject TO current directory", file=sys.stderr)
        sys.exit(1)

    remote_parent_path = sys.argv[1]
    current_dir = Path.cwd()
    current_basename = current_dir.name
    parent_dir = current_dir.parent

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

    # Construct the source path (remote subdirectory)
    source = remote_parent / current_basename

    # Validate that the source subdirectory exists
    if not source.exists():
        print(
            f"Error: Source subdirectory does not exist: {source}", file=sys.stderr
        )
        print(
            f"Expected to find a subdirectory named '{current_basename}' in {remote_parent}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not source.is_dir():
        print(f"Error: Source path is not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    print(f"Synchronizing FROM: {source.resolve()}", file=sys.stderr)
    print(f"              TO: {current_dir.resolve()}", file=sys.stderr)
    print("", file=sys.stderr)

    # Perform synchronization: source is remote subdirectory, destination is parent of current dir
    sync_directories(source, parent_dir)


if __name__ == "__main__":
    main()
