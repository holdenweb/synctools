"""
Integration tests for sync_directories function.

Tests the core synchronization logic with various combinations
of local and remote sources/destinations.
"""

import pytest
import sys
from pathlib import Path
import subprocess

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synctools.sync_dirs import (
    sync_directories,
    check_rsync_available,
    build_rsync_command
)
from synctools.file_path import FilePath, LocalFile, SSHFile
from conftest import rsync_available, ssh_available


class TestCheckRsyncAvailable:
    """Tests for rsync availability checking."""
    
    @rsync_available
    def test_rsync_is_available(self):
        """Should return True when rsync is available."""
        assert check_rsync_available()
    
    def test_rsync_command(self):
        """Should build correct rsync command."""
        source = LocalFile("/tmp/source")
        dest = LocalFile("/tmp/dest")
        
        cmd = build_rsync_command(source, dest)
        
        assert cmd[0] == "rsync"
        assert "-avh" in cmd
        assert "--progress" in cmd
        assert "--delete" in cmd
        assert "--stats" in cmd
        assert cmd[-2].endswith("/")  # Source should have trailing slash
        assert cmd[-1].endswith("/")  # Dest should have trailing slash


class TestSyncLocalToLocal:
    """Tests for synchronization between local directories."""
    
    @rsync_available
    def test_sync_basic(
        self, 
        populated_source, 
        empty_dest_parent, 
        verify_sync
    ):
        """Should sync files from source to destination."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        sync_directories(source, dest_parent)
        
        # Verify files were copied
        dest_dir = empty_dest_parent / populated_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    def test_sync_creates_destination(
        self,
        populated_source,
        empty_dest_parent,
        test_file_content
    ):
        """Should create destination directory if it doesn't exist."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        dest_dir = empty_dest_parent / populated_source.name
        assert not dest_dir.exists()
        
        sync_directories(source, dest_parent)
        
        assert dest_dir.exists()
        assert dest_dir.is_dir()
    
    @rsync_available
    def test_sync_preserves_structure(
        self,
        populated_source,
        empty_dest_parent
    ):
        """Should preserve directory structure."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        sync_directories(source, dest_parent)
        
        dest_dir = empty_dest_parent / populated_source.name
        
        # Check subdirectories exist
        assert (dest_dir / "subdir").exists()
        assert (dest_dir / "subdir" / "nested").exists()
    
    @rsync_available
    def test_sync_updates_changed_files(
        self,
        populated_source,
        empty_dest_parent,
        test_file_content
    ):
        """Should update files that have changed."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        # First sync
        sync_directories(source, dest_parent)
        
        dest_dir = empty_dest_parent / populated_source.name
        
        # Modify a file in source
        modified_file = populated_source / "file1.txt"
        new_content = "MODIFIED CONTENT"
        modified_file.write_text(new_content)
        
        # Second sync
        sync_directories(source, dest_parent)
        
        # Verify file was updated
        dest_file = dest_dir / "file1.txt"
        assert dest_file.read_text() == new_content
    
    @rsync_available
    def test_sync_deletes_extra_files(
        self,
        populated_source,
        empty_dest_parent
    ):
        """Should delete files in destination that don't exist in source."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        # First sync
        sync_directories(source, dest_parent)
        
        dest_dir = empty_dest_parent / populated_source.name
        
        # Add extra file to destination
        extra_file = dest_dir / "extra_file.txt"
        extra_file.write_text("This should be deleted")
        assert extra_file.exists()
        
        # Second sync
        sync_directories(source, dest_parent)
        
        # Verify extra file was deleted
        assert not extra_file.exists()
    
    @rsync_available
    def test_sync_with_special_filenames(
        self,
        populated_source,
        empty_dest_parent
    ):
        """Should handle files with spaces and special characters."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        sync_directories(source, dest_parent)
        
        dest_dir = empty_dest_parent / populated_source.name
        
        # Verify special filenames were synced
        assert (dest_dir / "file with spaces.txt").exists()
        assert (dest_dir / "file-with-special!@#.txt").exists()
    
    @rsync_available
    def test_sync_empty_directory(
        self,
        temp_local_dir,
        empty_dest_parent
    ):
        """Should handle empty source directory."""
        empty_source = temp_local_dir / "empty_source"
        empty_source.mkdir()
        
        source = LocalFile(str(empty_source))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        sync_directories(source, dest_parent)
        
        dest_dir = empty_dest_parent / empty_source.name
        assert dest_dir.exists()
        assert dest_dir.is_dir()
        # Directory should be empty
        assert list(dest_dir.iterdir()) == []


@pytest.mark.ssh
class TestSyncLocalToRemote:
    """Tests for synchronization from local to remote directories."""
    
    @rsync_available
    @ssh_available
    def test_sync_to_remote(
        self,
        populated_source,
        empty_remote_dest_parent,
        remote_host,
        verify_sync
    ):
        """Should sync local files to remote destination."""
        source = LocalFile(str(populated_source))
        dest_parent = SSHFile(f"{remote_host}:{empty_remote_dest_parent}")
        
        sync_directories(source, dest_parent)
        
        # Verify files were copied (check locally since it's localhost)
        dest_dir = empty_remote_dest_parent / populated_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    @ssh_available
    def test_sync_to_remote_creates_destination(
        self,
        populated_source,
        empty_remote_dest_parent,
        remote_host
    ):
        """Should create remote destination directory."""
        source = LocalFile(str(populated_source))
        dest_parent = SSHFile(f"{remote_host}:{empty_remote_dest_parent}")
        
        dest_dir = empty_remote_dest_parent / populated_source.name
        assert not dest_dir.exists()
        
        sync_directories(source, dest_parent)
        
        # Verify directory was created
        assert dest_dir.exists()
        assert dest_dir.is_dir()
    
    @rsync_available
    @ssh_available
    def test_sync_to_remote_with_special_chars(
        self,
        populated_source,
        empty_remote_dest_parent,
        remote_host
    ):
        """Should handle special characters in filenames to remote."""
        source = LocalFile(str(populated_source))
        dest_parent = SSHFile(f"{remote_host}:{empty_remote_dest_parent}")
        
        sync_directories(source, dest_parent)
        
        dest_dir = empty_remote_dest_parent / populated_source.name
        assert (dest_dir / "file with spaces.txt").exists()
        assert (dest_dir / "file-with-special!@#.txt").exists()


@pytest.mark.ssh
class TestSyncRemoteToLocal:
    """Tests for synchronization from remote to local directories."""
    
    @rsync_available
    @ssh_available
    def test_sync_from_remote(
        self,
        populated_remote_source,
        empty_dest_parent,
        remote_host,
        verify_sync
    ):
        """Should sync remote files to local destination."""
        source = SSHFile(f"{remote_host}:{populated_remote_source}")
        dest_parent = LocalFile(str(empty_dest_parent))
        
        sync_directories(source, dest_parent)
        
        # Verify files were copied
        dest_dir = empty_dest_parent / populated_remote_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    @ssh_available
    def test_sync_from_remote_with_special_chars(
        self,
        populated_remote_source,
        empty_dest_parent,
        remote_host
    ):
        """Should handle special characters from remote source."""
        source = SSHFile(f"{remote_host}:{populated_remote_source}")
        dest_parent = LocalFile(str(empty_dest_parent))
        
        sync_directories(source, dest_parent)
        
        dest_dir = empty_dest_parent / populated_remote_source.name
        assert (dest_dir / "file with spaces.txt").exists()
        assert (dest_dir / "file-with-special!@#.txt").exists()


@pytest.mark.ssh
class TestSyncRemoteToRemote:
    """Tests for synchronization between remote directories."""
    
    @rsync_available
    @ssh_available
    def test_sync_remote_to_remote(
        self,
        populated_remote_source,
        temp_remote_dir,
        remote_host,
        verify_sync
    ):
        """Should sync between two remote locations."""
        # Create separate destination parent
        dest_parent_dir = temp_remote_dir / "remote_dest_parent"
        dest_parent_dir.mkdir()
        
        source = SSHFile(f"{remote_host}:{populated_remote_source}")
        dest_parent = SSHFile(f"{remote_host}:{dest_parent_dir}")
        
        sync_directories(source, dest_parent)
        
        # Verify files were copied (check locally)
        dest_dir = dest_parent_dir / populated_remote_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"


class TestSyncErrorHandling:
    """Tests for error detection and reporting."""
    
    @rsync_available
    def test_source_does_not_exist(self, empty_dest_parent, capsys):
        """Should report error when source doesn't exist."""
        source = LocalFile("/tmp/nonexistent_source_xyz")
        dest_parent = LocalFile(str(empty_dest_parent))
        
        with pytest.raises(SystemExit):
            source.validate("Source directory")
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.err
    
    @rsync_available
    def test_source_not_directory(self, temp_local_dir, empty_dest_parent, capsys):
        """Should report error when source is not a directory."""
        source_file = temp_local_dir / "source_file.txt"
        source_file.write_text("not a directory")
        
        source = LocalFile(str(source_file))
        dest_parent = LocalFile(str(empty_dest_parent))
        
        with pytest.raises(SystemExit):
            source.validate("Source directory")
        
        captured = capsys.readouterr()
        assert "not a directory" in captured.err
    
    @rsync_available
    def test_dest_parent_does_not_exist(self, populated_source, capsys):
        """Should report error when dest parent doesn't exist."""
        source = LocalFile(str(populated_source))
        dest_parent = LocalFile("/tmp/nonexistent_parent_xyz")
        
        with pytest.raises(SystemExit):
            dest_parent.validate("Destination parent directory")
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.err
    
    @pytest.mark.ssh
    @ssh_available
    def test_remote_source_does_not_exist(
        self,
        empty_dest_parent,
        remote_host,
        capsys
    ):
        """Should report error when remote source doesn't exist."""
        source = SSHFile(f"{remote_host}:/tmp/nonexistent_remote_xyz")
        
        with pytest.raises(SystemExit):
            source.validate("Source directory")
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.err
    
    def test_invalid_ssh_path_format(self):
        """Should raise ValueError for invalid SSH path format."""
        with pytest.raises(ValueError):
            SSHFile("/local/path/without/colon")
