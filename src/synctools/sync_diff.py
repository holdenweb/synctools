#!/usr/bin/env python3
"""
Directory Comparison Script for synctools.

Compares the current working directory with a local or remote directory,
showing which files are newer, older, or unique to each location.

Usage:
    sync_diff <remote_parent_dir>

This helps determine which direction to sync before running sync_to or sync_from.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .file_path import FilePath, LocalFile, SSHFile


class FileStatus(Enum):
    """Status of a file comparison."""
    NEWER = "NEWER"          # Local file is newer than remote
    OLDER = "OLDER"          # Local file is older than remote
    SAME = "SAME"            # Files are identical (mtime and size)
    LOCAL_ONLY = "LOCAL_ONLY"    # File exists only locally
    REMOTE_ONLY = "REMOTE_ONLY"  # File exists only remotely
    CONFLICT = "CONFLICT"    # Both exist but can't determine which is newer


@dataclass
class FileInfo:
    """Information about a file."""
    path: str  # Relative path
    size: int
    mtime: float
    exists: bool = True


@dataclass
class ComparisonResult:
    """Result of comparing two files."""
    path: str
    status: FileStatus
    local_info: Optional[FileInfo]
    remote_info: Optional[FileInfo]


def get_local_file_info(base_path: Path, rel_path: str) -> Optional[FileInfo]:
    """
    Get information about a local file.
    
    Args:
        base_path: Base directory path
        rel_path: Relative path to file
        
    Returns:
        FileInfo or None if file doesn't exist
    """
    full_path = base_path / rel_path
    
    if not full_path.exists():
        return None
    
    if full_path.is_dir():
        return None  # Skip directories
    
    stat = full_path.stat()
    return FileInfo(
        path=rel_path,
        size=stat.st_size,
        mtime=stat.st_mtime
    )


def get_remote_file_info(remote_base: SSHFile, rel_path: str) -> Optional[FileInfo]:
    """
    Get information about a remote file via SSH.
    
    Args:
        remote_base: Remote base directory
        rel_path: Relative path to file
        
    Returns:
        FileInfo or None if file doesn't exist
    """
    # Construct full remote path
    remote_file = remote_base.join(rel_path)
    
    # Use SSH to get file info
    # stat -f "%z %m" gives size and mtime on macOS
    # stat -c "%s %Y" gives size and mtime on Linux
    # We'll try both
    
    cmd_linux = f'stat -c "%s %Y" {remote_file._remote_path} 2>/dev/null'
    cmd_macos = f'stat -f "%z %m" {remote_file._remote_path} 2>/dev/null'
    
    try:
        # Try Linux format first
        result = subprocess.run(
            ['ssh', remote_file._host, cmd_linux],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                return FileInfo(
                    path=rel_path,
                    size=int(parts[0]),
                    mtime=float(parts[1])
                )
        
        # Try macOS format
        result = subprocess.run(
            ['ssh', remote_file._host, cmd_macos],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                return FileInfo(
                    path=rel_path,
                    size=int(parts[0]),
                    mtime=float(parts[1])
                )
        
        return None
        
    except (subprocess.SubprocessError, ValueError):
        return None


def list_local_files(base_path: Path) -> List[str]:
    """
    List all files in a directory recursively.
    
    Args:
        base_path: Base directory path
        
    Returns:
        List of relative paths
    """
    files = []
    for root, dirs, filenames in os.walk(base_path):
        for filename in filenames:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(base_path)
            files.append(str(rel_path))
    
    return sorted(files)


def list_remote_files(remote_base: SSHFile) -> List[str]:
    """
    List all files in a remote directory recursively via SSH.
    
    Args:
        remote_base: Remote base directory
        
    Returns:
        List of relative paths
    """
    # Use find command to list all files
    cmd = f'cd {remote_base._remote_path} && find . -type f | sed "s|^./||"'
    
    try:
        result = subprocess.run(
            ['ssh', remote_base._host, cmd],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            files = [
                line.strip() 
                for line in result.stdout.splitlines() 
                if line.strip() and line.strip() != '.'
            ]
            return sorted(files)
        
        return []
        
    except subprocess.SubprocessError:
        return []


def compare_files(
    local_base: Path,
    remote_base: FilePath,
    verbose: bool = False
) -> List[ComparisonResult]:
    """
    Compare files between local and remote directories.
    
    Args:
        local_base: Local directory path
        remote_base: Remote directory FilePath
        verbose: Whether to include detailed file info
        
    Returns:
        List of ComparisonResult objects
    """
    results = []
    
    # Get all files from both locations
    local_files = set(list_local_files(local_base))
    
    if isinstance(remote_base, LocalFile):
        remote_files = set(list_local_files(Path(remote_base._pathobj)))
    else:
        remote_files = set(list_remote_files(remote_base))
    
    # Get all unique file paths
    all_files = local_files | remote_files
    
    for rel_path in sorted(all_files):
        local_info = get_local_file_info(local_base, rel_path)
        
        if isinstance(remote_base, LocalFile):
            remote_info = get_local_file_info(Path(remote_base._pathobj), rel_path)
        else:
            remote_info = get_remote_file_info(remote_base, rel_path)
        
        # Determine status
        if local_info and remote_info:
            # Both exist - compare
            if abs(local_info.mtime - remote_info.mtime) < 1.0:
                # Within 1 second - consider same (filesystem precision)
                if local_info.size == remote_info.size:
                    status = FileStatus.SAME
                else:
                    status = FileStatus.CONFLICT
            elif local_info.mtime > remote_info.mtime:
                status = FileStatus.NEWER
            else:
                status = FileStatus.OLDER
        elif local_info and not remote_info:
            status = FileStatus.LOCAL_ONLY
        elif remote_info and not local_info:
            status = FileStatus.REMOTE_ONLY
        else:
            continue  # Neither exists? Skip
        
        results.append(ComparisonResult(
            path=rel_path,
            status=status,
            local_info=local_info,
            remote_info=remote_info
        ))
    
    return results


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:6.1f}{unit}"
        size /= 1024.0
    return f"{size:6.1f}TB"


def format_timestamp(mtime: float) -> str:
    """Format timestamp in human-readable format."""
    from datetime import datetime
    dt = datetime.fromtimestamp(mtime)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def print_results(results: List[ComparisonResult], verbose: bool = False):
    """
    Print comparison results.
    
    Args:
        results: List of comparison results
        verbose: Whether to include detailed file info
    """
    # Count by status
    counts = {status: 0 for status in FileStatus}
    for result in results:
        counts[result.status] += 1
    
    # Print header
    print("=" * 80, file=sys.stderr)
    print("Directory Comparison Results", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(file=sys.stderr)
    
    # Print summary
    print("Summary:", file=sys.stderr)
    print(f"  {counts[FileStatus.NEWER]:4d} files are NEWER locally (consider sync_to)", file=sys.stderr)
    print(f"  {counts[FileStatus.OLDER]:4d} files are OLDER locally (consider sync_from)", file=sys.stderr)
    print(f"  {counts[FileStatus.SAME]:4d} files are the SAME", file=sys.stderr)
    print(f"  {counts[FileStatus.LOCAL_ONLY]:4d} files exist only LOCALLY", file=sys.stderr)
    print(f"  {counts[FileStatus.REMOTE_ONLY]:4d} files exist only REMOTELY", file=sys.stderr)
    if counts[FileStatus.CONFLICT] > 0:
        print(f"  {counts[FileStatus.CONFLICT]:4d} files have CONFLICTS (same mtime, different size)", file=sys.stderr)
    print(file=sys.stderr)
    
    # Print details
    if verbose:
        print("Detailed Comparison:", file=sys.stderr)
        print("-" * 80, file=sys.stderr)
        
        for result in results:
            print(f"\n{result.status.value:12s} {result.path}", file=sys.stderr)
            
            if result.local_info:
                print(f"  Local:  {format_size(result.local_info.size):>10s}  "
                      f"{format_timestamp(result.local_info.mtime)}", file=sys.stderr)
            else:
                print(f"  Local:  (not present)", file=sys.stderr)
            
            if result.remote_info:
                print(f"  Remote: {format_size(result.remote_info.size):>10s}  "
                      f"{format_timestamp(result.remote_info.mtime)}", file=sys.stderr)
            else:
                print(f"  Remote: (not present)", file=sys.stderr)
    else:
        # Print just the files that differ
        print("Files requiring attention:", file=sys.stderr)
        print("-" * 80, file=sys.stderr)
        
        for result in results:
            if result.status != FileStatus.SAME:
                print(f"{result.status.value:12s} {result.path}", file=sys.stderr)
    
    print(file=sys.stderr)
    print("=" * 80, file=sys.stderr)


def main():
    """Main function for sync_diff command."""
    verbose = False
    
    # Parse arguments
    args = sys.argv[1:]
    if '--verbose' in args or '-v' in args:
        verbose = True
        args = [arg for arg in args if arg not in ('--verbose', '-v')]
    
    if len(args) != 1:
        print("Usage: sync_diff [--verbose] <remote_parent_dir>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Compares current directory with <remote_parent_dir>/$(basename $PWD)", file=sys.stderr)
        print("", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --verbose, -v  Show detailed file information", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  cd /home/user/myproject", file=sys.stderr)
        print("  sync_diff /backup", file=sys.stderr)
        print("  # Compares current directory with /backup/myproject", file=sys.stderr)
        print("", file=sys.stderr)
        print("  sync_diff user@server:/backup", file=sys.stderr)
        print("  # Compares current directory with user@server:/backup/myproject", file=sys.stderr)
        sys.exit(1)
    
    remote_parent_path = args[0]
    
    # Get current directory
    current_dir = Path.cwd()
    current_basename = current_dir.name
    
    # Create FilePath for remote parent
    remote_parent = FilePath.create(remote_parent_path)
    
    # Validate remote parent exists
    remote_parent.validate("Remote parent directory")
    
    # Construct remote directory path
    remote_dir = remote_parent.join(current_basename)
    
    # Check if remote directory exists
    if not remote_dir.exists():
        print(f"Error: Remote directory does not exist: {remote_dir.for_display()}", file=sys.stderr)
        print(f"Expected to find a directory named '{current_basename}' in {remote_parent.for_display()}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Comparing LOCAL: {current_dir}", file=sys.stderr)
    print(f"     with REMOTE: {remote_dir.for_display()}", file=sys.stderr)
    print(file=sys.stderr)
    
    # Compare directories
    results = compare_files(current_dir, remote_dir, verbose)
    
    # Print results
    print_results(results, verbose)


if __name__ == "__main__":
    main()
