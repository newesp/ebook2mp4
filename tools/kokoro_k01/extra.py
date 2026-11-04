"""Additional same-text warm measurement and cancellation during actual weight loading."""
import json
import os
import time
from run import Worker, SAMPLES, EVIDENCE


def main():
    assert os.environ.get('K01_FIREWALL_ACTIVE') == '1'
    current = None
    results = []
    try:
        current = Worker('cancel-model-load')
        current.wait('model_loading',600)
        time.sleep(.3)
        results.append(current.finish('cancel'))
        current = Worker('warm-repeat')
        current.wait('ready',600)
        previews = []
        for index in range(2):
            # Use a distinct sample identifier to preserve all previous recordings.
            sample = dict(SAMPLES[0], id=f'warm-repeat-{index+1}')
            current.send(dict(action='synthesize',sample=sample,voice='zf_001'))
            previews.append(current.wait('completed'))
        results.append(current.finish('close'))
        current = None
        (EVIDENCE/'extra-lifecycle.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        (EVIDENCE/'same-text-warm.json').write_text(json.dumps(previews,indent=2),encoding='utf-8')
    finally:
        if current is not None:
            current.finish('cancel')


if __name__=='__main__':
    main()
