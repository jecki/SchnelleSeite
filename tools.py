# general tool functions for SchnelleSeite

import contextlib
import os


@contextlib.contextmanager
def enter_dir(directory):
    """Context manager for temporarily descending into a specific directory."""
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


@contextlib.contextmanager
def create_and_enter_dir(directory):
    """Context manager for creating a directory (unless it already exists) and
    temporarily descending into it."""
    if not os.path.exists(directory):
        os.mkdir(directory)
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)
