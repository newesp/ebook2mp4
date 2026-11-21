"""Run selected workflows with workflow.py loaded from the production EXE.

This uses the developer interpreter, not the standalone GUI or a clean Windows.
Run from the repository with PYTHONPATH=.;tests;.scratch/build-tools.
"""
import os
from pathlib import Path
import unittest

from PyInstaller.archive.readers import CArchiveReader
import ebook2mp4.workflow as workflow

root = Path.cwd()
distribution = root / 'dist/ebook2mp4'
archive = CArchiveReader(str(distribution / 'ebook2mp4.exe')).open_embedded_archive('PYZ.pyz')
exec(archive.extract('ebook2mp4.workflow'), workflow.__dict__)
tools = distribution / '_internal/tools/ffmpeg'
os.environ['EBOOK2MP4_FFMPEG'] = str(tools / 'ffmpeg.exe')
os.environ['EBOOK2MP4_FFPROBE'] = str(tools / 'ffprobe.exe')
os.environ['PATH'] = str(tools) + os.pathsep + os.environ['PATH']
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'test_narration_resume.NarrationRecovery.test_resume_rejects_a_project_changed_in_another_window',
    'test_kokoro_narration.LocalNarration.test_local_cancel_corrupt_cache_resume_and_pause_reuse',
    'test_outputs.OutputsJourney.test_moved_partial_project_finishes_video_without_new_speech',
])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
