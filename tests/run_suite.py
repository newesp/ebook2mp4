"""Run native tests with Tk object collection kept on the owning main thread."""
import gc
from pathlib import Path
import sys
import unittest
import re


class NativeResult(unittest.TextTestResult):
    def stopTest(self,test):
        super().stopTest(test)
        # Tk test roots are destroyed in cleanup. Reclaim their remaining cycles
        # here, before the next VoiceJob can trigger collection on its worker.
        gc.collect()


if __name__=='__main__':
    loader=unittest.defaultTestLoader
    names=[name for name in sys.argv[1:] if not name.startswith('-')]
    suite=loader.loadTestsFromNames(names) if names else loader.discover(str(Path(__file__).parent))
    resume=next((arg.split('=',1)[1] for arg in sys.argv[1:] if arg.startswith('--resume-log=')),None)
    if resume:
        completed=set(re.findall(r'^test_\S+ \(([^)]+)\) \.\.\. (?:ok|skipped .*)$',
                                 Path(resume).read_text(encoding='utf-8-sig'),re.M))
        def cases(tests):
            for test in tests:
                if isinstance(test,unittest.TestSuite):yield from cases(test)
                else:yield test
        pending=[test for test in cases(suite) if test.id() not in completed]
        print(f'Resuming {len(pending)} cases; {len(completed)} already completed.',flush=True)
        suite=unittest.TestSuite(pending)
    result=unittest.TextTestRunner(verbosity=2,resultclass=NativeResult).run(suite)
    sys.exit(not result.wasSuccessful())
