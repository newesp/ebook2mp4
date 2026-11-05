"""A batch adapter for the shared video workflow; book storage stays unchanged."""
from copy import deepcopy
import inspect
from .workflow import ProjectWorkflow, ProjectError


class BatchVideoTarget:
    KEYS = ('total_video_settings', 'total_video', 'total_video_runs')

    def __init__(self, project, batch_id):
        project._batch(batch_id)
        self.project = project
        self.batch_id = batch_id

    def __getattr__(self, name):
        # Existing public total-video methods run against this target's storage.
        if 'total_video' in name:
            descriptor = inspect.getattr_static(ProjectWorkflow, name, None)
            if isinstance(descriptor, staticmethod):
                return descriptor.__func__
            method = getattr(ProjectWorkflow, name, None)
            if method is not None:
                return method.__get__(self, type(self))
        return getattr(self.project, name)

    @property
    def _total_video_job(self):
        return self.project._total_video_job

    @_total_video_job.setter
    def _total_video_job(self, job):
        self.project._total_video_job = job

    @property
    def state(self):
        manifest = self.project.state
        saved = self.project._batch(self.batch_id).get('video', {})
        for key in self.KEYS:
            manifest.pop(key, None)
            if key in saved:
                manifest[key] = deepcopy(saved[key])
        return manifest

    def _commit(self, manifest, files):
        original = self.project.state
        saved = {key: manifest.pop(key) for key in self.KEYS if key in manifest}
        batch = next((b for b in manifest['batches'] if b['id'] == self.batch_id), None)
        if batch is None:
            raise ProjectError('批次已移除，請重新開啟專案。')
        batch['video'] = saved
        for key in self.KEYS:
            if key in original:
                manifest[key] = original[key]
        self.project._commit(manifest, files)

    def audio(self, *, verify_media=False):
        from .assembly import source_ref
        ref = source_ref(self.project, self.batch_id, verify_media=verify_media)
        product = self.project._batch(self.batch_id)['narration']
        return dict(id=ref['product_id'], mp3=ref['mp3'], srt=ref['srt'],
                    duration_ms=product['duration_ms'])

    async def inspect_audio(self):
        self.project._check_current()
        from .assembly import checked_file_async
        product = self.audio()
        for kind in ('mp3', 'srt'):
            await checked_file_async(self.project, product[kind])
        return dict(product, stale=False)
