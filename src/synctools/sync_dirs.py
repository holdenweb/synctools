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

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Tuple, Union


def is_remote_path(path: str) -> bool:
    """
    Check if a path is a remote SSH location.
    
    Args:
        path: Path string to check
        
    Returns:
        True if path matches SSH remote format (user@host:/path or host:/path)
    """
    # Match patterns like user@host:/path or host:/path
    remote_pattern = r'^([a-zA-Z0-9_-]+@)?[a-zA-Z0-9._-]+:.+'
    return bool(re.match(remote_pattern, path))


def parse_remote_path(path: str) -> Tuple[str, str]:
    """
    Parse a remote SSH path into host and path components.
    
    Args:
        path: Remote path in format user@host:/path or host:/path
        
    Returns:
        Tuple of (host_part, path_part) where host_part includes user@ if present
    """
    if ':' in path:
        host_part, path_part = path.split(':', 1)
        return host_part, path_part
    return '', path


def join_remote_path(host_part: str, *path_parts: str) -> str:
    """
    Join path components for a remote SSH location.
    
    Args:
        host_part: The user@host or host portion
        *path_parts: Path components to join
        
    Returns:
        Complete remote path string
    """
    # Join path parts with forward slashes
    joined_path = '/'.join(str(p).strip('/') for p in path_parts if p)
    return f"{host_part}:{joined_path}"


def get_basename(path: str) -> str:
    """
    Get the basename of a path (works for both local and remote paths).
    
    Args:
        path: Local or remote path
        
    Returns:
        The basename (last component) of the path
    """
    if is_remote_path(path):
        _, path_part = parse_remote_path(path)
        return Path(path_part).name
    else:
        return Path(path).name


def validate_local_directory(path: str, arg_name: str) -> Path:
    """
    Validate that a local path exists and is a directory.

    Args:
        path: Path string to validate
        arg_name: Name of the argument (for error messages)

    Returns:
        Path object if valid

    Raises:
        SystemExit: If validation fails
    """
    path_obj = Path(path)

    if not path_obj.exists():
        print(f"Error: {arg_name} does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    if not path_obj.is_dir():
        print(f"Error: {arg_name} is not a directory: {path}", file=sys.stderr)
        sys.exit(1)

    return path_obj


def validate_remote_directory(path: str, arg_name: str) -> bool:
    """
    Validate that a remote SSH path exists and is a directory.
    
    Args:
        path: Remote path string to validate
        arg_name: Name of the argument (for error messages)
        
    Returns:
        True if valid
        
    Raises:
        SystemExit: If validation fails
    """
    host_part, path_part = parse_remote_path(path)
    
    # Use SSH to check if the remote path exists and is a directory
    try:
        result = subprocess.run(
            ["ssh", host_part, f"test -d {path_part}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"Error: {arg_name} does not exist or is not a directory: {path}", file=sys.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        print("Error: ssh command not found. SSH is required for remote paths.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unable to validate remote path {path}: {e}", file=sys.stderr)
        sys.exit(1)


def validate_directory(path: str, arg_name: str) -> Union[Path, str]:
    """
    Validate that a path exists and is a directory (local or remote).
    
    Args:
        path: Path string to validate (local or remote)
        arg_name: Name of the argument (for error messages)
        
    Returns:
        Path object for local paths, string for remote paths
        
    Raises:
        SystemExit: If validation fails
    """
    if is_remote_path(path):
        validate_remote_directory(path, arg_name)
        return path
    else:
        return validate_local_directory(path, arg_name)


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


def create_destination_directory(dest_path: Union[Path, str]) -> None:
    """
    Create destination directory if it doesn't exist.
    
    Args:
        dest_path: Destination path (Path object for local, string for remote)
    """
    if isinstance(dest_path, Path):
        # Local path - use mkdir
        dest_path.mkdir(parents=True, exist_ok=True)
    else:
        # Remote path - use SSH to create directory
        host_part, path_part = parse_remote_path(dest_path)
        try:
            subprocess.run(
                ["ssh", host_part, f"mkdir -p {path_part}"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not create remote directory {dest_path}: {e}", file=sys.stderr)
            print("rsync will attempt to create it if needed.", file=sys.stderr)
        except FileNotFoundError:
            print("Warning: ssh command not found. rsync will attempt to create directory.", file=sys.stderr)


def format_path_for_display(path: Union[Path, str]) -> str:
    """
    Format a path for display (resolve local paths, return remote as-is).
    
    Args:
        path: Path to format
        
    Returns:
        Formatted path string
    """
    if isinstance(path, Path):
        return str(path.resolve())
    else:
        return path


def build_rsync_command(source: Union[Path, str], destination: Union[Path, str]) -> List[str]:
    """
    Build the rsync command with appropriate options.

    Args:
        source: Source directory path (Path object or string)
        destination: Destination directory path (Path object or string)

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

    # Convert Path objects to strings and ensure trailing slashes
    source_str = str(source)
    dest_str = str(destination)
    
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


def sync_directories(source: Union[Path, str], dest_parent: Union[Path, str]) -> None:
    """
    Synchronize source directory to a subdirectory of dest_parent.

    Args:
        source: Source directory to sync from (Path object or remote string)
        dest_parent: Parent directory where subdirectory will be created/synced
    """
    # Get the name of the source directory
    source_name = get_basename(str(source))

    # Build the full destination path
    if isinstance(dest_parent, Path):
        # Local destination parent
        destination = dest_parent / source_name
    else:
        # Remote destination parent
        host_part, path_part = parse_remote_path(dest_parent)
        destination = join_remote_path(host_part, path_part, source_name)

    # Create destination directory if it doesn't exist
    create_destination_directory(destination)

    print(f"Source directory: {format_path_for_display(source)}", file=sys.stderr)
    print(f"Destination directory: {format_path_for_display(destination)}", file=sys.stderr)
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

    # Validate directories
    source = validate_directory(source_path, "Source directory")
    dest_parent = validate_directory(dest_parent_path, "Destination parent directory")

    # Perform synchronization
    sync_directories(source, dest_parent)


if __name__ == "__main__":
    main()
