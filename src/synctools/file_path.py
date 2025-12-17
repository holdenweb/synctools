#!/usr/bin/env python3
"""
File path abstraction for local and remote SSH paths.

Provides a unified interface for working with both local filesystem paths
and remote SSH locations.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod


class FilePath(ABC):
    """
    Abstract base class for file paths (local or remote).
    
    Provides a common interface for path operations that work
    across both local filesystem paths and remote SSH locations.
    """
    
    def __init__(self, path: str):
        """
        Initialize a FilePath.
        
        Args:
            path: Path string (local or remote)
        """
        self._path = path
    
    @staticmethod
    def create(path: str) -> 'FilePath':
        """
        Factory method to create appropriate FilePath subclass.
        
        Args:
            path: Path string to wrap
            
        Returns:
            LocalFile or SSHFile instance depending on path format
        """
        if SSHFile.is_ssh_path(path):
            return SSHFile(path)
        else:
            return LocalFile(path)
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if the path exists."""
        pass
    
    @abstractmethod
    def is_dir(self) -> bool:
        """Check if the path is a directory."""
        pass
    
    @abstractmethod
    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory at this path."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the basename (last component) of the path."""
        pass
    
    @abstractmethod
    def join(self, *parts: str) -> 'FilePath':
        """Join path components and return a new FilePath."""
        pass
    
    @abstractmethod
    def for_display(self) -> str:
        """Get a formatted string suitable for display to users."""
        pass
    
    @abstractmethod
    def for_rsync(self) -> str:
        """Get the path string formatted for use with rsync."""
        pass
    
    def __str__(self) -> str:
        """String representation (same as for_rsync)."""
        return self.for_rsync()
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"{self.__class__.__name__}('{self._path}')"
    
    def validate(self, arg_name: str) -> None:
        """
        Validate that this path exists and is a directory.
        
        Args:
            arg_name: Name for error messages
            
        Raises:
            SystemExit: If validation fails
        """
        if not self.exists():
            print(f"Error: {arg_name} does not exist: {self.for_display()}", file=sys.stderr)
            sys.exit(1)
        
        if not self.is_dir():
            print(f"Error: {arg_name} is not a directory: {self.for_display()}", file=sys.stderr)
            sys.exit(1)


class LocalFile(FilePath):
    """
    Represents a local filesystem path.
    
    Wraps Python's pathlib.Path and provides the FilePath interface.
    """
    
    def __init__(self, path: str):
        """
        Initialize a LocalFile.
        
        Args:
            path: Local filesystem path string
        """
        super().__init__(path)
        self._pathobj = Path(path)
    
    def exists(self) -> bool:
        """Check if the local path exists."""
        return self._pathobj.exists()
    
    def is_dir(self) -> bool:
        """Check if the local path is a directory."""
        return self._pathobj.is_dir()
    
    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
        """Create local directory."""
        self._pathobj.mkdir(parents=parents, exist_ok=exist_ok)
    
    def get_name(self) -> str:
        """Get the basename of the local path."""
        return self._pathobj.name
    
    def join(self, *parts: str) -> 'LocalFile':
        """Join path components and return a new LocalFile."""
        new_path = self._pathobj.joinpath(*parts)
        return LocalFile(str(new_path))
    
    def for_display(self) -> str:
        """Get resolved absolute path for display."""
        return str(self._pathobj.resolve())
    
    def for_rsync(self) -> str:
        """Get the path string for rsync (uses the original path)."""
        return str(self._pathobj)
    
    def get_parent(self) -> 'LocalFile':
        """Get the parent directory as a LocalFile."""
        return LocalFile(str(self._pathobj.parent))
    
    def cwd(self) -> str:
        """Get current working directory name."""
        return self._pathobj.name


class SSHFile(FilePath):
    """
    Represents a remote SSH file path.
    
    Handles paths in the format user@host:/path or host:/path.
    Uses SSH commands to perform operations on the remote system.
    """
    
    # Pattern to match SSH paths: [user@]host:/path
    SSH_PATTERN = re.compile(r'^([a-zA-Z0-9_-]+@)?[a-zA-Z0-9._-]+:.+')
    
    def __init__(self, path: str):
        """
        Initialize an SSHFile.
        
        Args:
            path: Remote SSH path in format user@host:/path or host:/path
        """
        super().__init__(path)
        
        if ':' not in path:
            raise ValueError(f"Invalid SSH path format: {path}")
        
        self._host, self._remote_path = path.split(':', 1)
    
    @staticmethod
    def is_ssh_path(path: str) -> bool:
        """
        Check if a path string is in SSH format.
        
        Args:
            path: Path string to check
            
        Returns:
            True if path matches SSH format
        """
        return bool(SSHFile.SSH_PATTERN.match(path))
    
    def exists(self) -> bool:
        """Check if the remote path exists using SSH."""
        return self._run_test('-e')
    
    def is_dir(self) -> bool:
        """Check if the remote path is a directory using SSH."""
        return self._run_test('-d')
    
    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
        """
        Create directory on remote system using SSH.
        
        Args:
            parents: If True, create parent directories as needed
            exist_ok: If True, don't error if directory exists
        """
        cmd = "mkdir"
        if parents:
            cmd += " -p"
        
        try:
            result = subprocess.run(
                ["ssh", self._host, f"{cmd} {self._remote_path}"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # If mkdir fails and exist_ok is False, raise an error
            if result.returncode != 0 and not exist_ok:
                raise OSError(f"Failed to create remote directory: {result.stderr}")
                
        except FileNotFoundError:
            raise OSError("ssh command not found. SSH is required for remote paths.")
    
    def get_name(self) -> str:
        """Get the basename of the remote path."""
        return Path(self._remote_path).name
    
    def join(self, *parts: str) -> 'SSHFile':
        """Join path components and return a new SSHFile."""
        # Join the remote path parts
        joined = '/'.join([self._remote_path.rstrip('/')] + [str(p).strip('/') for p in parts if p])
        new_path = f"{self._host}:{joined}"
        return SSHFile(new_path)
    
    def for_display(self) -> str:
        """Get the SSH path for display (returns as-is)."""
        return self._path
    
    def for_rsync(self) -> str:
        """Get the SSH path formatted for rsync."""
        return self._path
    
    def _run_test(self, test_flag: str) -> bool:
        """
        Run a test command on the remote system via SSH.
        
        Args:
            test_flag: Flag for the test command (e.g., '-e', '-d', '-f')
            
        Returns:
            True if test passes, False otherwise
        """
        try:
            result = subprocess.run(
                ["ssh", self._host, f"test {test_flag} {self._remote_path}"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
            
        except FileNotFoundError:
            raise OSError("ssh command not found. SSH is required for remote paths.")
    
    def _run_command(self, command: str) -> subprocess.CompletedProcess:
        """
        Run a command on the remote system via SSH.
        
        Args:
            command: Shell command to execute on remote system
            
        Returns:
            CompletedProcess instance
        """
        try:
            return subprocess.run(
                ["ssh", self._host, command],
                capture_output=True,
                text=True,
                check=False
            )
        except FileNotFoundError:
            raise OSError("ssh command not found. SSH is required for remote paths.")
