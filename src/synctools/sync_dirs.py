#!/usr/bin/env python3
"""
Directory Synchronization Script using rsync.

Usage:
    python sync_dirs.py <source_dir> <destination_parent_dir>

This script synchronizes the source directory to a subdirectory of the destination
parent directory. The subdirectory will have the same name as the source directory.

Supports both local paths and remote SSH locations (user@host:/path or host:/path).

Example:
    python sync_dirs.py /home/user/documents /backup
    python sync_dirs.py /home/user/documents user@server:/backup
    python sync_dirs.py user@server:/data /backup
"""

import sys
import subprocess
from typing import List
from .file_path import FilePath


def check_rsync_available() -> bool:
    """
    Check if rsync is available on the system.

    Returns:
        True if rsync is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["rsync", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def build_rsync_command(source: FilePath, destination: FilePath) -> List[str]:
    """
    Build the rsync command with appropriate options.

    Args:
        source: Source directory FilePath
        destination: Destination directory FilePath

    Returns:
        List of command arguments for subprocess
    """
    # rsync options:
    # -a: archive mode (recursive, preserves permissions, times, symlinks, etc.)
    # -v: verbose output
    # -h: human-readable output
    # --progress: show progress during transfer
    # --delete: delete files in destination that don't exist in source
    # --stats: show file transfer statistics

    # Get path strings for rsync and ensure trailing slashes
    source_str = source.for_rsync()
    dest_str = destination.for_rsync()
    
    # Add trailing slashes to ensure contents are synced, not the directory itself
    if not source_str.endswith('/'):
        source_str += '/'
    if not dest_str.endswith('/'):
        dest_str += '/'

    command = [
        "rsync",
        "-avh",
        "--progress",
        "--delete",
        "--stats",
        source_str,
        dest_str
    ]

    return command


def sync_directories(source: FilePath, dest_parent: FilePath) -> None:
    """
    Synchronize source directory to a subdirectory of dest_parent.

    Args:
        source: Source directory to sync from
        dest_parent: Parent directory where subdirectory will be created/synced
    """
    # Get the name of the source directory
    source_name = source.get_name()

    # Build the full destination path
    destination = dest_parent.join(source_name)

    # Create destination directory if it doesn't exist
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create destination directory: {e}", file=sys.stderr)
        print("rsync will attempt to create it if needed.", file=sys.stderr)

    print(f"Source directory: {source.for_display()}", file=sys.stderr)
    print(f"Destination directory: {destination.for_display()}", file=sys.stderr)
    print(f"\nSynchronizing...\n", file=sys.stderr)

    # Build rsync command
    command = build_rsync_command(source, destination)

    # Show the command being executed
    print(f"Executing: {' '.join(command)}\n", file=sys.stderr)

    try:
        # Run rsync with real-time output
        result = subprocess.run(
            command,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print(f"\n✓ Synchronization completed successfully!", file=sys.stderr)
        else:
            print(f"\n✗ rsync exited with code {result.returncode}", file=sys.stderr)
            sys.exit(result.returncode)

    except KeyboardInterrupt:
        print(f"\n\nSynchronization interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError during synchronization: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function to handle command line arguments and orchestrate sync."""
    # Check arguments
    if len(sys.argv) != 3:
        print("Usage: python sync_dirs.py <source_dir> <destination_parent_dir>", file=sys.stderr)
        print("\nArguments:", file=sys.stderr)
        print("  source_dir              Source directory to synchronize (local or remote)", file=sys.stderr)
        print("  destination_parent_dir  Parent directory for the synchronized copy (local or remote)", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  python sync_dirs.py /home/user/documents /backup", file=sys.stderr)
        print("  → Syncs to /backup/documents/", file=sys.stderr)
        print("  python sync_dirs.py /home/user/documents user@server:/backup", file=sys.stderr)
        print("  → Syncs to user@server:/backup/documents/", file=sys.stderr)
        print("  python sync_dirs.py user@server:/data /backup", file=sys.stderr)
        print("  → Syncs to /backup/data/", file=sys.stderr)
        sys.exit(1)

    source_path = sys.argv[1]
    dest_parent_path = sys.argv[2]

    # Check if rsync is available
    if not check_rsync_available():
        print("Error: rsync is not available on this system.", file=sys.stderr)
        print("Please install rsync:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt-get install rsync", file=sys.stderr)
        print("  macOS: brew install rsync (or use built-in version)", file=sys.stderr)
        print("  Windows: Install via WSL, Cygwin, or msys2", file=sys.stderr)
        sys.exit(1)

    # Create FilePath objects (automatically detects local vs remote)
    source = FilePath.create(source_path)
    dest_parent = FilePath.create(dest_parent_path)

    # Validate directories
    source.validate("Source directory")
    dest_parent.validate("Destination parent directory")

    # Perform synchronization
    sync_directories(source, dest_parent)


if __name__ == "__main__":
    main()
