"""
Unit tests for the FilePath class hierarchy.

Tests LocalFile and SSHFile classes for correct behavior.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synctools.file_path import FilePath, LocalFile, SSHFile


class TestFilePathFactory:
    """Tests for the FilePath.create() factory method."""
    
    def test_create_local_path(self):
        """Factory should return LocalFile for local paths."""
        path = FilePath.create("/tmp/test")
        assert isinstance(path, LocalFile)
    
    def test_create_ssh_path_with_user(self):
        """Factory should return SSHFile for user@host:path format."""
        path = FilePath.create("user@host:/tmp/test")
        assert isinstance(path, SSHFile)
    
    def test_create_ssh_path_without_user(self):
        """Factory should return SSHFile for host:path format."""
        path = FilePath.create("host:/tmp/test")
        assert isinstance(path, SSHFile)
    
    def test_create_relative_path(self):
        """Factory should return LocalFile for relative paths."""
        path = FilePath.create("relative/path")
        assert isinstance(path, LocalFile)
    
    def test_create_home_path(self):
        """Factory should return LocalFile for paths starting with ~."""
        path = FilePath.create("~/documents")
        assert isinstance(path, LocalFile)


class TestSSHFilePatternDetection:
    """Tests for SSH path pattern detection."""
    
    def test_is_ssh_path_with_user(self):
        """Should detect user@host:path as SSH path."""
        assert SSHFile.is_ssh_path("user@host:/tmp/test")
    
    def test_is_ssh_path_without_user(self):
        """Should detect host:path as SSH path."""
        assert SSHFile.is_ssh_path("server:/home/data")
    
    def test_is_not_ssh_path_local(self):
        """Should not detect local paths as SSH paths."""
        assert not SSHFile.is_ssh_path("/tmp/test")
        assert not SSHFile.is_ssh_path("relative/path")
    
    def test_is_not_ssh_path_windows(self):
        """Should not detect Windows paths as SSH paths (C:/path)."""
        assert not SSHFile.is_ssh_path("C:/Users/test")
    
    def test_is_ssh_path_with_subdomain(self):
        """Should detect SSH paths with subdomains."""
        assert SSHFile.is_ssh_path("user@server.example.com:/data")
    
    def test_is_ssh_path_with_hyphen(self):
        """Should detect SSH paths with hyphens in hostname."""
        assert SSHFile.is_ssh_path("user@my-server:/data")
    
    def test_is_ssh_path_with_underscore(self):
        """Should detect SSH paths with underscores in username."""
        assert SSHFile.is_ssh_path("my_user@host:/data")


class TestLocalFile:
    """Tests for LocalFile class."""
    
    def test_get_name(self, temp_local_dir):
        """Should return basename of path."""
        path = LocalFile(str(temp_local_dir / "testdir"))
        assert path.get_name() == "testdir"
    
    def test_exists_true(self, temp_local_dir):
        """Should return True for existing path."""
        test_dir = temp_local_dir / "exists"
        test_dir.mkdir()
        path = LocalFile(str(test_dir))
        assert path.exists()
    
    def test_exists_false(self, temp_local_dir):
        """Should return False for non-existing path."""
        path = LocalFile(str(temp_local_dir / "does_not_exist"))
        assert not path.exists()
    
    def test_is_dir_true(self, temp_local_dir):
        """Should return True for directory."""
        test_dir = temp_local_dir / "testdir"
        test_dir.mkdir()
        path = LocalFile(str(test_dir))
        assert path.is_dir()
    
    def test_is_dir_false_for_file(self, temp_local_dir):
        """Should return False for file."""
        test_file = temp_local_dir / "testfile.txt"
        test_file.write_text("test")
        path = LocalFile(str(test_file))
        assert not path.is_dir()
    
    def test_mkdir(self, temp_local_dir):
        """Should create directory."""
        new_dir = temp_local_dir / "newdir"
        path = LocalFile(str(new_dir))
        path.mkdir()
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_mkdir_parents(self, temp_local_dir):
        """Should create parent directories."""
        nested = temp_local_dir / "parent" / "child"
        path = LocalFile(str(nested))
        path.mkdir(parents=True)
        assert nested.exists()
        assert nested.is_dir()
    
    def test_join(self, temp_local_dir):
        """Should join path components correctly."""
        base = LocalFile(str(temp_local_dir))
        joined = base.join("subdir", "file.txt")
        
        assert isinstance(joined, LocalFile)
        assert "subdir" in str(joined)
        assert "file.txt" in str(joined)
    
    def test_for_display(self, temp_local_dir):
        """Should return absolute path for display."""
        path = LocalFile(str(temp_local_dir))
        display = path.for_display()
        assert Path(display).is_absolute()
    
    def test_for_rsync(self, temp_local_dir):
        """Should return path string for rsync."""
        path = LocalFile(str(temp_local_dir))
        rsync_path = path.for_rsync()
        assert str(temp_local_dir) in rsync_path
    
    def test_validate_success(self, temp_local_dir):
        """Should not raise for valid directory."""
        test_dir = temp_local_dir / "valid"
        test_dir.mkdir()
        path = LocalFile(str(test_dir))
        path.validate("Test directory")  # Should not raise
    
    def test_validate_not_exists(self, temp_local_dir, capsys):
        """Should exit with error if path doesn't exist."""
        path = LocalFile(str(temp_local_dir / "missing"))
        with pytest.raises(SystemExit) as exc_info:
            path.validate("Test directory")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.err
    
    def test_validate_not_directory(self, temp_local_dir, capsys):
        """Should exit with error if path is not a directory."""
        test_file = temp_local_dir / "file.txt"
        test_file.write_text("test")
        path = LocalFile(str(test_file))
        
        with pytest.raises(SystemExit) as exc_info:
            path.validate("Test directory")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.err
    
    def test_str_representation(self, temp_local_dir):
        """Should have reasonable string representation."""
        path = LocalFile(str(temp_local_dir))
        str_repr = str(path)
        assert str(temp_local_dir) in str_repr


class TestSSHFile:
    """Tests for SSHFile class."""
    
    def test_init_with_user(self):
        """Should parse user@host:path correctly."""
        path = SSHFile("user@host:/tmp/test")
        assert path._host == "user@host"
        assert path._remote_path == "/tmp/test"
    
    def test_init_without_user(self):
        """Should parse host:path correctly."""
        path = SSHFile("host:/tmp/test")
        assert path._host == "host"
        assert path._remote_path == "/tmp/test"
    
    def test_init_invalid_format(self):
        """Should raise ValueError for invalid format."""
        with pytest.raises(ValueError):
            SSHFile("/local/path")
    
    def test_get_name(self):
        """Should return basename of remote path."""
        path = SSHFile("host:/tmp/testdir")
        assert path.get_name() == "testdir"
    
    def test_join(self):
        """Should join remote path components correctly."""
        base = SSHFile("user@host:/tmp")
        joined = base.join("subdir", "file.txt")
        
        assert isinstance(joined, SSHFile)
        assert joined._host == "user@host"
        assert "subdir" in joined._remote_path
        assert "file.txt" in joined._remote_path
    
    def test_join_with_trailing_slash(self):
        """Should handle trailing slashes correctly."""
        base = SSHFile("host:/tmp/")
        joined = base.join("subdir")
        
        # Should not have double slashes
        assert "//" not in joined._remote_path
    
    def test_for_display(self):
        """Should return SSH path for display."""
        path = SSHFile("user@host:/tmp/test")
        assert path.for_display() == "user@host:/tmp/test"
    
    def test_for_rsync(self):
        """Should return SSH path for rsync."""
        path = SSHFile("user@host:/tmp/test")
        assert path.for_rsync() == "user@host:/tmp/test"
    
    def test_str_representation(self):
        """Should have reasonable string representation."""
        path = SSHFile("user@host:/tmp/test")
        str_repr = str(path)
        assert "user@host:/tmp/test" in str_repr
    
    @pytest.mark.ssh
    def test_exists_true(self, remote_host, temp_remote_dir):
        """Should return True for existing remote path."""
        path = SSHFile(f"{remote_host}:{temp_remote_dir}")
        assert path.exists()
    
    @pytest.mark.ssh
    def test_exists_false(self, remote_host, temp_remote_dir):
        """Should return False for non-existing remote path."""
        path = SSHFile(f"{remote_host}:{temp_remote_dir}/does_not_exist")
        assert not path.exists()
    
    @pytest.mark.ssh
    def test_is_dir_true(self, remote_host, temp_remote_dir):
        """Should return True for remote directory."""
        path = SSHFile(f"{remote_host}:{temp_remote_dir}")
        assert path.is_dir()
    
    @pytest.mark.ssh
    def test_is_dir_false_for_file(self, remote_host, temp_remote_dir):
        """Should return False for remote file."""
        test_file = temp_remote_dir / "testfile.txt"
        test_file.write_text("test")
        path = SSHFile(f"{remote_host}:{test_file}")
        assert not path.is_dir()
    
    @pytest.mark.ssh
    def test_mkdir(self, remote_host, temp_remote_dir):
        """Should create remote directory."""
        new_dir = temp_remote_dir / "newdir"
        path = SSHFile(f"{remote_host}:{new_dir}")
        path.mkdir()
        assert new_dir.exists()
    
    @pytest.mark.ssh
    def test_mkdir_parents(self, remote_host, temp_remote_dir):
        """Should create remote parent directories."""
        nested = temp_remote_dir / "parent" / "child"
        path = SSHFile(f"{remote_host}:{nested}")
        path.mkdir(parents=True)
        assert nested.exists()
    
    @pytest.mark.ssh
    def test_validate_success(self, remote_host, temp_remote_dir):
        """Should not raise for valid remote directory."""
        path = SSHFile(f"{remote_host}:{temp_remote_dir}")
        path.validate("Test remote directory")  # Should not raise
    
    @pytest.mark.ssh
    def test_validate_not_exists(self, remote_host, temp_remote_dir, capsys):
        """Should exit with error if remote path doesn't exist."""
        path = SSHFile(f"{remote_host}:{temp_remote_dir}/missing")
        with pytest.raises(SystemExit) as exc_info:
            path.validate("Test directory")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.err


class TestFilePathPolymorphism:
    """Tests to ensure LocalFile and SSHFile are interchangeable."""
    
    def test_common_interface_local(self, temp_local_dir):
        """LocalFile should implement all FilePath methods."""
        test_dir = temp_local_dir / "test"
        test_dir.mkdir()
        path = LocalFile(str(test_dir))
        
        # All these methods should exist and work
        assert hasattr(path, 'exists')
        assert hasattr(path, 'is_dir')
        assert hasattr(path, 'mkdir')
        assert hasattr(path, 'get_name')
        assert hasattr(path, 'join')
        assert hasattr(path, 'for_display')
        assert hasattr(path, 'for_rsync')
        assert hasattr(path, 'validate')
    
    def test_common_interface_ssh(self):
        """SSHFile should implement all FilePath methods."""
        path = SSHFile("host:/tmp/test")
        
        # All these methods should exist
        assert hasattr(path, 'exists')
        assert hasattr(path, 'is_dir')
        assert hasattr(path, 'mkdir')
        assert hasattr(path, 'get_name')
        assert hasattr(path, 'join')
        assert hasattr(path, 'for_display')
        assert hasattr(path, 'for_rsync')
        assert hasattr(path, 'validate')
