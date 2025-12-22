"""
Tests for sync_to and sync_from commands.

Tests the high-level command functions that change directory
and invoke sync_directories.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synctools import sync_to, sync_from
from synctools.file_path import FilePath, LocalFile, SSHFile
from conftest import rsync_available, ssh_available


class TestSyncToLocal:
    """Tests for sync_to command with local destinations."""
    
    @rsync_available
    def test_sync_to_local(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd,
        verify_sync
    ):
        """Should sync current directory to local destination."""
        # Change to source directory
        os.chdir(populated_source)
        
        # Mock sys.argv
        with patch.object(sys, 'argv', ['sync_to', str(empty_dest_parent)]):
            sync_to()
        
        # Verify files were synced
        dest_dir = empty_dest_parent / populated_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    def test_sync_to_creates_destination(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd
    ):
        """Should create destination subdirectory."""
        os.chdir(populated_source)
        
        dest_dir = empty_dest_parent / populated_source.name
        assert not dest_dir.exists()
        
        with patch.object(sys, 'argv', ['sync_to', str(empty_dest_parent)]):
            sync_to()
        
        assert dest_dir.exists()
        assert dest_dir.is_dir()
    
    @rsync_available
    def test_sync_to_wrong_args(self, populated_source, original_cwd, capsys):
        """Should show usage message with wrong number of arguments."""
        os.chdir(populated_source)
        
        with patch.object(sys, 'argv', ['sync_to']):
            with pytest.raises(SystemExit):
                sync_to()
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.err
    
    @rsync_available
    def test_sync_to_no_rsync(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd,
        capsys
    ):
        """Should report error when rsync is not available."""
        os.chdir(populated_source)
        
        with patch('synctools.check_rsync_available', return_value=False):
            with patch.object(sys, 'argv', ['sync_to', str(empty_dest_parent)]):
                with pytest.raises(SystemExit):
                    sync_to()
        
        captured = capsys.readouterr()
        assert "rsync is not available" in captured.err
    
    @rsync_available
    def test_sync_to_dest_not_exists(
        self,
        populated_source,
        temp_local_dir,
        original_cwd,
        capsys
    ):
        """Should report error when destination parent doesn't exist."""
        os.chdir(populated_source)
        
        nonexistent = temp_local_dir / "does_not_exist"
        
        with patch.object(sys, 'argv', ['sync_to', str(nonexistent)]):
            with pytest.raises(SystemExit):
                sync_to()
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.err


@pytest.mark.ssh
class TestSyncToRemote:
    """Tests for sync_to command with remote destinations."""
    
    @rsync_available
    @ssh_available
    def test_sync_to_remote(
        self,
        populated_source,
        empty_remote_dest_parent,
        remote_host,
        original_cwd,
        verify_sync
    ):
        """Should sync current directory to remote destination."""
        os.chdir(populated_source)
        
        remote_path = f"{remote_host}:{empty_remote_dest_parent}"
        
        with patch.object(sys, 'argv', ['sync_to', remote_path]):
            sync_to()
        
        # Verify files were synced (check locally since it's localhost)
        dest_dir = empty_remote_dest_parent / populated_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"


class TestSyncFromLocal:
    """Tests for sync_from command with local sources."""
    
    @rsync_available
    def test_sync_from_local(
        self,
        populated_source,
        temp_local_dir,
        original_cwd,
        verify_sync
    ):
        """Should sync from local source to current directory."""
        # Create a directory to sync into (with different name to avoid conflict)
        dest_dir = temp_local_dir / "dest_for_sync_from"
        dest_dir.mkdir()
        # Create subdirectory matching source name
        sync_target = dest_dir / populated_source.name
        sync_target.mkdir()
        os.chdir(sync_target)
        
        # Parent of populated_source is the "remote parent"
        source_parent = populated_source.parent
        
        with patch.object(sys, 'argv', ['sync_from', str(source_parent)]):
            sync_from()
        
        # Verify files were synced
        errors = verify_sync(sync_target)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    def test_sync_from_source_not_exists(
        self,
        temp_local_dir,
        original_cwd,
        capsys
    ):
        """Should report error when source subdirectory doesn't exist."""
        # Create current directory
        current_dir = temp_local_dir / "myproject"
        current_dir.mkdir()
        os.chdir(current_dir)
        
        # Create parent directory without the subdirectory
        source_parent = temp_local_dir / "source_parent"
        source_parent.mkdir()
        # Note: source_parent/myproject does NOT exist
        
        with patch.object(sys, 'argv', ['sync_from', str(source_parent)]):
            with pytest.raises(SystemExit):
                sync_from()
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.err
    
    @rsync_available
    def test_sync_from_wrong_args(
        self,
        temp_local_dir,
        original_cwd,
        capsys
    ):
        """Should show usage message with wrong number of arguments."""
        os.chdir(temp_local_dir)
        
        with patch.object(sys, 'argv', ['sync_from']):
            with pytest.raises(SystemExit):
                sync_from()
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.err


@pytest.mark.ssh
class TestSyncFromRemote:
    """Tests for sync_from command with remote sources."""
    
    @rsync_available
    @ssh_available
    def test_sync_from_remote(
        self,
        populated_remote_source,
        temp_local_dir,
        remote_host,
        original_cwd,
        verify_sync
    ):
        """Should sync from remote source to current directory."""
        # Create local directory to sync into
        dest_dir = temp_local_dir / populated_remote_source.name
        dest_dir.mkdir()
        os.chdir(dest_dir)
        
        # Parent of remote source
        source_parent = populated_remote_source.parent
        remote_path = f"{remote_host}:{source_parent}"
        
        with patch.object(sys, 'argv', ['sync_from', remote_path]):
            sync_from()
        
        # Verify files were synced
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    @ssh_available
    def test_sync_from_remote_not_exists(
        self,
        temp_local_dir,
        temp_remote_dir,
        remote_host,
        original_cwd,
        capsys
    ):
        """Should handle non-existent remote subdirectory gracefully."""
        # Create local directory
        current_dir = temp_local_dir / "myproject"
        current_dir.mkdir()
        os.chdir(current_dir)
        
        # Create remote parent without subdirectory
        remote_parent = temp_remote_dir / "remote_parent"
        remote_parent.mkdir()
        remote_path = f"{remote_host}:{remote_parent}"
        # Note: remote_parent/myproject does NOT exist
        
        # For remote sources, we don't validate the subdirectory exists
        # beforehand, so rsync will fail. This tests the rsync failure path.
        with patch.object(sys, 'argv', ['sync_from', remote_path]):
            with pytest.raises(SystemExit):
                sync_from()


class TestCommandEdgeCases:
    """Tests for edge cases in command handling."""
    
    @rsync_available
    def test_sync_to_with_symlinks(
        self,
        temp_local_dir,
        empty_dest_parent,
        original_cwd
    ):
        """Should handle symlinks in source directory."""
        # Create source with symlink
        source_dir = temp_local_dir / "source_with_link"
        source_dir.mkdir()
        
        target_file = source_dir / "target.txt"
        target_file.write_text("target content")
        
        link_file = source_dir / "link.txt"
        link_file.symlink_to(target_file)
        
        os.chdir(source_dir)
        
        with patch.object(sys, 'argv', ['sync_to', str(empty_dest_parent)]):
            sync_to()
        
        dest_dir = empty_dest_parent / source_dir.name
        assert dest_dir.exists()
        # rsync -a preserves symlinks
        assert (dest_dir / "link.txt").exists()
    
    @rsync_available
    def test_sync_to_empty_directory(
        self,
        temp_local_dir,
        empty_dest_parent,
        original_cwd
    ):
        """Should handle empty source directory."""
        empty_source = temp_local_dir / "empty"
        empty_source.mkdir()
        
        os.chdir(empty_source)
        
        with patch.object(sys, 'argv', ['sync_to', str(empty_dest_parent)]):
            sync_to()
        
        dest_dir = empty_dest_parent / empty_source.name
        assert dest_dir.exists()
        assert list(dest_dir.iterdir()) == []
    
    @rsync_available
    def test_sync_preserves_permissions(
        self,
        temp_local_dir,
        empty_dest_parent,
        original_cwd
    ):
        """Should preserve file permissions."""
        source_dir = temp_local_dir / "source_perms"
        source_dir.mkdir()
        
        # Create file with specific permissions
        test_file = source_dir / "executable.sh"
        test_file.write_text("#!/bin/bash\necho test")
        test_file.chmod(0o755)
        
        original_mode = test_file.stat().st_mode
        
        os.chdir(source_dir)
        
        with patch.object(sys, 'argv', ['sync_to', str(empty_dest_parent)]):
            sync_to()
        
        dest_file = empty_dest_parent / source_dir.name / "executable.sh"
        dest_mode = dest_file.stat().st_mode
        
        # rsync -a preserves permissions
        assert original_mode == dest_mode
