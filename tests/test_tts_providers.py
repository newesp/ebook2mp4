import base64,json,unittest
from unittest.mock import patch
import test_voice as fixture
from ebook2mp4.tts_services import save_profile,profiles
from ebook2mp4.workflow import ProjectWorkflow

class Providers(unittest.TestCase):
    setUp=fixture.VoiceJourney.setUp
    audio=fixture.VoiceJourney.audio
    def test_gemini_custom_model_preview_formal_reuse_and_no_project_key(self):
        identity=save_profile('Google','gemini-tts','synthetic-secret')
        value=self.flow.voice_settings(self.batch)
        value.update(provider='gemini-tts',profile=identity,model='future-tts-model',voice='Kore')
        payload=self.audio();requests=[]
        class Content:
            async def iter_chunked(self,n):
                yield json.dumps(dict(steps=[dict(type='model_output',content=[dict(type='audio',data=base64.b64encode(payload).decode())])])).encode()
        class Response:
            status=200;content=Content()
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
        class Session:
            def __init__(self,**kwargs):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            def post(self,url,**kwargs):requests.append((url,kwargs));return Response()
        with patch('aiohttp.ClientSession',Session):
            job=self.flow.start_voice_preview(self.batch,text='Hello.',start=0,end=6,settings_override=value)
            self.assertTrue(job.wait(15));self.assertEqual(job.state['status'],'completed',job.state)
            preview=self.flow.finish_voice_preview(job)
            self.flow.save_voice_settings('Kore',batch_id=self.batch,settings_override=value)
            self.flow.save_draft(self.batch,'Hello.');self.flow.confirm_reading(self.batch)
            job=self.flow.start_narration(self.batch);self.assertTrue(job.wait(15));product=self.flow.finish_narration(job)
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0][1]['json']['model'],'future-tts-model')
        self.assertEqual(requests[0][1]['headers']['x-goog-api-key'],'synthetic-secret')
        self.assertTrue(product['chunks'][0]['reused'])
        self.assertNotIn('synthetic-secret',json.dumps(self.flow.state))
        self.assertEqual(ProjectWorkflow.open(self.flow.root).voice_settings(self.batch)['model'],'future-tts-model')
        self.assertNotIn('synthetic-secret',json.dumps(profiles()))

    def test_fish_request_and_auth_error_preserve_previous_result(self):
        from ebook2mp4.workflow import ProjectError
        identity=save_profile('Fish','fish-audio','fish-test-secret')
        value=self.flow.voice_settings(self.batch);value.update(provider='fish-audio',profile=identity,model='s2.1-pro',voice='my-voice-id')
        payload=self.audio();requests=[];status=[200]
        class Content:
            async def iter_chunked(self,n):yield payload
        class Response:
            content=Content()
            @property
            def status(self):return status[0]
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
        class Session:
            def __init__(self,**kwargs):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            def post(self,url,**kwargs):requests.append((url,kwargs));return Response()
        with patch('aiohttp.ClientSession',Session):
            job=self.flow.start_voice_preview(self.batch,text='Fish.',start=0,end=5,settings_override=value)
            self.assertTrue(job.wait(15));previous=self.flow.finish_voice_preview(job)
            status[0]=401
            job=self.flow.start_voice_preview(self.batch,text='Different.',start=0,end=10,settings_override=value)
            self.assertTrue(job.wait(15));self.assertEqual(job.state['status'],'failed')
            self.assertIn('401',job.state['error']);self.flow.discard_voice_preview(job)
        self.assertEqual(self.flow.voice_preview(self.batch)['id'],previous['id'])
        self.assertEqual(len(requests),2)
        self.assertEqual(requests[0][1]['json']['reference_id'],'my-voice-id')
        self.assertEqual(requests[0][1]['headers']['model'],'s2.1-pro')
        self.assertNotIn('fish-test-secret',job.state['error'])

    def test_profile_provider_cannot_change_and_fish_model_is_explicit(self):
        from ebook2mp4.workflow import ProjectError
        from ebook2mp4.voice import settings
        identity=save_profile('Google','gemini-tts','key-one')
        with self.assertRaises(ProjectError):save_profile('Fish','fish-audio',profile_id=identity)
        value=self.flow.voice_settings(self.batch)
        value.update(provider='fish-audio',profile=identity,model='misspelled-free',voice='id')
        with self.assertRaises(ProjectError):settings(value)
        self.assertEqual(profiles()[identity]['provider'],'gemini-tts')


class ProviderDesktop(unittest.TestCase):
    setUp=__import__('test_voice_desktop').VoiceDesktop.setUp
    def test_service_switch_enables_model_and_management_layout(self):
        from ebook2mp4.service_desktop import ServiceDialog
        identity=save_profile('Google','gemini-tts','synthetic-key')
        self.dialog.reload_services()
        self.assertEqual(str(self.dialog.model_control.cget('state')),'disabled')
        self.dialog.service.set(self.dialog.service_labels[identity]);self.dialog.change_service()
        self.assertEqual(str(self.dialog.model_control.cget('state')),'normal')
        self.dialog.model.set('future-voice-model');self.dialog.voice.set('Kore')
        self.assertEqual(self.dialog.current_settings()['model'],'future-voice-model')
        self.dialog.service.set('Edge-TTS');self.dialog.change_service()
        self.assertEqual(str(self.dialog.model_control.cget('state')),'disabled')
        window=ServiceDialog(self.dialog);self.addCleanup(window.close);self.root.update()
        self.assertEqual(int(window.status.grid_info()['row']),8)

    def test_check_service_reads_complete_chunked_json(self):
        import time
        from ebook2mp4.service_desktop import ServiceDialog
        window=ServiceDialog(self.dialog);self.addCleanup(window.close)
        window.key.set('test-key')
        class Content:
            async def iter_chunked(self,n):
                yield b'{"voices":'
                yield b'[]}'
        class Response:
            status=200;content=Content()
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
        class Session:
            def __init__(self,**kwargs):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            def get(self,*args,**kwargs):return Response()
        with patch('aiohttp.ClientSession',Session):
            window.check_button.invoke()
            deadline=time.monotonic()+5
            while window.job is not None and time.monotonic()<deadline:self.root.update();time.sleep(.01)
        self.assertIsNone(window.job)
        self.assertIn('檢查通過',window.status.cget('text'))
