"""Native voice chooser and preview; no editor lock or automatic voice choice."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .workflow import ProjectError
from .voice import EXAMPLE, RATES
from .voice_media import PreviewPlayer


PLAYING_PREVIEW = '正在播放上次成功試聽。'


class VoiceDialog(ttk.Frame):
    page_id = 'voice.preview'
    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job = None
        self.kind = ''
        self.timer = None
        self.closing = False
        self.local_package_selection=None
        self.player = PreviewPlayer()
        from .voice_workspace import VoiceWorkspaceLayout
        self.workspace_layout = VoiceWorkspaceLayout(self, app)
        self.rhythm_traces = [(variable, variable.trace_add('write', self.rhythm_changed))
                              for variable in (self.sentence_pause, self.paragraph_pause)]
        self.load_settings()
        self.refresh_setting_sources()
        self.edit_traces = [(v, v.trace_add('write', self.settings_edited)) for v in
                            (self.voice, self.rate, self.model, self.service, self.sentence_pause, self.paragraph_pause)]
        self.prepare_text()
        self.load_result()
        self.update_controls()

    def reflow(self, event):
        settings=event.widget in (self.settings_panel,self.settings_scroll.content)
        labels = ((self.cache_info, self.rules_info, self.rate_info)
                  if settings else
                  (self.status, self.result_info, self.text_info))
        width=self.settings_scroll.content.winfo_width() if settings else event.width-28
        for label in labels:
            label.configure(wraplength=max(1,width))
        if settings:
            for label in (self.sentence_label,self.paragraph_label):
                label.configure(wraplength=max(1,(width-6)//2))
            narrow=width<self.filter.winfo_reqwidth()+self.refresh_button.winfo_reqwidth()+4
            self.filter.grid_configure(columnspan=2 if narrow else 1,padx=0 if narrow else (0,4))
            self.refresh_button.grid_configure(row=1 if narrow else 0,column=0 if narrow else 1,
                columnspan=2 if narrow else 1,sticky='ew' if narrow else '',pady=(4,0) if narrow else 0)

    def reload_services(self):
        from .tts_services import profiles
        self.service_labels={'edge-tts':'Edge-TTS'}
        self.service_labels['kokoro']='Kokoro · 本機 CPU'
        self.service_labels.update({k:v['name']+' · '+k[:6] for k,v in profiles().items()})
        self.service_ids={v:k for k,v in self.service_labels.items()}
        self.service_control.configure(values=tuple(self.service_ids))

    def provider_name(self):
        from .tts_services import profiles
        identity=self.service_ids.get(self.service.get(),'edge-tts')
        if identity=='kokoro':return 'kokoro'
        if identity=='edge-tts': return 'edge-tts'
        value=profiles().get(identity)
        if value is None: raise ProjectError('本機尚未連結此服務，請在管理服務重新設定。')
        return value['provider']

    def change_service(self, _event=None):
        provider=self.provider_name()
        if provider=='kokoro':
            from .kokoro_packages import release
            self.local_package_selection=release()['id']
        self.voice.set('')
        self.model.set('v1.1 zh（官方）' if provider=='kokoro' else 'gemini-3.8-flash-lite-tts' if provider=='gemini-tts' else 's2.1-pro' if provider=='fish-audio' else '')
        self.load_catalog()
        self.update_controls()
        self.status.configure(text='服務已切換；請重新選音色及試聽，尚未儲存。')

    def save_and_produce(self):
        if self.scope.get()!='本批次':
            self.status.configure(text='請選本批次後再前往製作。');return
        try: self.flow.reading_text(self.batch_id)
        except ProjectError as error:
            self.status.configure(text=str(error));return
        if self.settings_dirty():
            self.status.configure(text='請先儲存設定。'); return
        self.app.narration()
        if self.loaded_run_id:
            self.app.narration_dialog.preferred_run_id = self.loaded_run_id

    def settings_dirty(self):
        try:
            return self.current_settings() != self.flow.voice_settings(self.batch_id if self.scope.get() == '本批次' else None)
        except (ProjectError, ValueError):
            return True

    def settings_edited(self, *_args):
        if hasattr(self, 'produce_button'):
            self.produce_button.configure(state='disabled' if self.job or self.settings_dirty() else 'normal')

    def refresh_setting_sources(self):
        try:
            self.setting_sources = self.flow.voice_setting_sources(self.batch_id if self.scope.get() == '本批次' else None)
            self.source_control.configure(values=[s['name'] for s in self.setting_sources])
            if self.setting_sources:
                self.sources_panel.grid()
                page = self.app.production.pages.get((id(self.flow), self.batch_id, 'narration'))
                run = getattr(page, 'run', None)
                selected = next((i for i,s in enumerate(self.setting_sources) if run and s.get('run_id') == run['snapshot']['id']), len(self.setting_sources)-1)
                self.source_control.current(selected)
            else:
                self.sources_panel.grid()
                self.source_choice.set('目前沒有已存設定')
        except ProjectError as error:
            self.source_control.configure(values=())
            self.status.configure(text=str(error))

    def load_selected_settings(self):
        if self.job or self.app.production.busy_for(self.flow): return
        index = self.source_control.current()
        if not 0 <= index < len(self.setting_sources): return
        if self.settings_dirty() and not messagebox.askyesno('載入設定', '取代尚未儲存的語音調整？', parent=self): return
        source = self.setting_sources[index]
        self.load_settings(value=source['settings'])
        self.loaded_run_id = source.get('run_id')
        self.stop()
        self.play_button.configure(state='disabled')
        self.status.configure(text='已載入：' + source['name'] + '。請儲存設定後前往製作。')
        self.update_controls()

    def manage_services(self):
        if self.job is not None: return
        self.app.production.manage_services(self)

    def update_service_menu(self):
        identity=self.service_ids.get(self.service.get())
        busy=self.job is not None or self.app.production.service_changes_busy()
        self.service_menu.entryconfigure(0,state='disabled' if busy else 'normal')
        local=identity=='kokoro'
        self.service_menu.entryconfigure(1,label='管理本機語音包…' if local else
                                         '編輯目前服務…（內建服務不適用）' if identity=='edge-tts' else '編輯目前服務…',
                                         state='disabled' if busy or identity=='edge-tts' else 'normal')

    def manage_current_service(self):
        if self.service_ids.get(self.service.get())=='kokoro': self.manage_local_packages()
        else: self.edit_service()

    def manage_local_packages(self):
        if self.job is None: self.app.production.manage_local_packages(self)

    def edit_service(self):
        identity=self.service_ids.get(self.service.get())
        if self.job is None and identity not in (None,'edge-tts','kokoro'):
            self.app.production.manage_services(self, profile_id=identity)

    def open_defaults(self):
        if self.job is not None or self.scope.get() != '全書預設':
            return
        try:
            if self.current_settings() != self.flow.voice_settings():
                raise ProjectError('請先儲存全書預設，再選擇要套用的批次。')
            if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
                raise ProjectError('書籍或批次已切換，請從目前批次重新開啟。')
            from .voice_defaults_desktop import VoiceDefaultsPage
            key = (id(self.flow), self.batch_id, 'defaults')
            page = self.app.production.pages.get(key)
            if page is None or not page.winfo_exists():
                page = VoiceDefaultsPage(self)
                self.app.production.pages[key] = page
            elif page.value != self.flow.voice_settings():
                page.value = self.flow.voice_settings()
                page.status.configure(text='全書預設已更新。保留批次選取，請重新核對套用後影響。')
            page.refresh()
            self.app.production.activate(page)
        except (ProjectError, ValueError) as error:
            self.status.configure(text=str(error))

    def load_settings(self, value=None):
        if value is None:
            value = self.flow.voice_settings(self.batch_id if self.scope.get() == '本批次' else None)
        self.local_package_selection=value.get('package')
        self.loaded_local_settings = dict(value)
        self.reload_services()
        identity='kokoro' if value['provider']=='kokoro' else value.get('profile','edge-tts')
        if identity not in self.service_labels:
            self.service_labels[identity]='未連結服務 · '+identity[:6]
            self.service_ids[self.service_labels[identity]]=identity
        self.service.set(self.service_labels[identity])
        self.model.set('v1.1 zh（官方）' if value['provider']=='kokoro' else value.get('model',''))
        self.voice.set(value['voice'])
        self.rate.set('正常' if value['rate'] == '+0%' else value['rate'])
        self.sentence_pause.set(str(value['sentence_pause_ms']))
        self.paragraph_pause.set(str(value['paragraph_pause_ms']))
        self.status.configure(text='全書預設僅供新批次；既有批次須明確套用。' if self.scope.get() == '全書預設'
                              else '本批次設定獨立保存。')
        self.load_catalog()
        self.update_controls()

    def apply_rhythm(self, _event=None):
        preset = {'自然': (0, 500), '舒緩': (200, 800)}.get(self.rhythm.get())
        if preset:
            self.sentence_pause.set(str(preset[0]))
            self.paragraph_pause.set(str(preset[1]))

    def rhythm_changed(self, *_args):
        pair = (self.sentence_pause.get(), self.paragraph_pause.get())
        self.rhythm.set({('0', '500'): '自然', ('200', '800'): '舒緩'}.get(pair, '自訂'))

    def load_catalog(self):
        try:
            from .tts_services import MODELS, VOICES
            provider = self.provider_name()
            edge = provider == 'edge-tts'
            self.model_control.configure(values=() if edge else
                                         ('s2.1-pro', 's2.1-pro-free') if provider == 'fish-audio' else MODELS)
            if provider=='kokoro':
                self.catalog_actions.grid_remove()
                packages=self.flow.local_voice_packages()
                choices=tuple(v['id'] for v in packages[0]['voices']) if packages else ()
                self.cache_info.configure(text=f'官方中文音色 {len(choices)} 種；尚無人工品質驗證音色。' if packages else '尚未安裝語音包。請按「管理本機語音包」。')
                self.model_control.configure(values=('v1.1 zh（官方）',))
            elif edge:
                self.catalog_actions.grid()
                catalog = self.flow.voice_catalog()
                locale = {'台灣華語': 'zh-TW', '中國普通話': 'zh-CN', '英文': 'en-'}.get(self.locale.get(), '')
                choices = tuple(v['id'] for v in catalog['voices'] if v['locale'].startswith(locale))
                self.cache_info.configure(text='更新：' + (catalog['updated_at'] or '尚未取得音色清單；更新不傳送書稿。'))
            else:
                self.catalog_actions.grid_remove()
                choices = VOICES if provider == 'gemini-tts' else ()
                self.cache_info.configure(text='內建音色候選，亦可手填 ID。' if provider == 'gemini-tts'
                                          else '輸入 Fish Audio 聲音 ID（reference_id）。')
            self.voice_control.configure(values=choices)
            if provider == 'fish-audio':
                self.voice_entry.grid()
                self.voice_control.grid_remove()
            else:
                self.voice_entry.grid_remove()
                self.voice_control.grid()
            self.voice_label.configure(text='聲音 ID（可直接輸入）' if provider == 'fish-audio' else '音色（可選或輸入 ID）')
            self.rate_info.configure(text='Gemini 語速以風格指示控制，請試聽確認。' if provider == 'gemini-tts' else '')
            if provider=='kokoro':
                self.consent_control.grid_remove()
                self.local_notice.grid(row=3,column=0,sticky='w',pady=2)
            else:
                self.local_notice.grid_remove();self.consent_control.grid()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def prepare_text(self):
        value = self.outgoing.get('1.0', 'end-1c')
        self.text_info.configure(text=f'{len(value):,}／3,000 字元')
        return value

    def replace_preview_text(self,text):
        if self.job:return
        current=self.outgoing.get('1.0','end-1c')
        if current not in ('',EXAMPLE,text):
            replace=messagebox.askyesnocancel('取代試聽文字',
                '目前有編輯過的試聽文字。\n是：取代文字。\n否：保留文字。\n取消：返回。',parent=self)
            if replace is not True:return
        self.outgoing.edit_separator()
        self.outgoing.delete('1.0','end');self.outgoing.insert('1.0',text)
        self.outgoing.edit_separator();self.prepare_text()

    def selected_preview_text(self):
        try:self.replace_preview_text(self.app.editor.get('sel.first','sel.last'))
        except tk.TclError:self.status.configure(text='請先在主稿選取文字，再返回並使用此命令。')

    def text_changed(self, _event=None):
        if self.outgoing.edit_modified():
            self.outgoing.edit_modified(False)
            self.prepare_text()

    def current_settings(self):
        from .voice import settings
        value = self.flow.voice_settings(self.batch_id if self.scope.get() == '本批次' else None)
        value.update(voice=self.voice.get(), rate='+0%' if self.rate.get() == '正常' else self.rate.get(),
                     sentence_pause_ms=int(self.sentence_pause.get()),
                     paragraph_pause_ms=int(self.paragraph_pause.get()))
        provider=self.provider_name()
        value['provider']=provider
        if provider=='kokoro':
            from .kokoro_packages import release
            metadata=release()
            previous=getattr(self, 'loaded_local_settings', self.flow.voice_settings(self.batch_id if self.scope.get()=='本批次' else None))
            identity=self.local_package_selection or metadata['id']
            use_current=identity==metadata['id']
            value.update(package=identity,model=metadata['model'] if use_current else previous.get('model',metadata['model']),
                         processing=metadata['processing'] if use_current else previous.get('processing',metadata['processing']))
            value.pop('profile',None)
        elif provider!='edge-tts':
            value.update(profile=self.service_ids.get(self.service.get(),''),model=self.model.get().strip())
            value.pop('package',None);value['processing']='identity-v1'
        else:
            value.pop('profile',None);value.pop('model',None)
            value.pop('package',None);value['processing']='identity-v1'
        return settings(value)

    def save(self, *, announce=True):
        if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
            self.status.configure(text='主視窗的書籍或批次已切換；請關閉本視窗，回目前批次重新開啟語音設定。')
            return False
        try:
            self.flow.save_voice_settings(self.voice.get(), '+0%' if self.rate.get() == '正常' else self.rate.get(),
                                          batch_id=self.batch_id if self.scope.get() == '本批次' else None,
                                          sentence_pause_ms=int(self.sentence_pause.get()),
                                          paragraph_pause_ms=int(self.paragraph_pause.get()),settings_override=self.current_settings())
            self.status.configure(text='語音設定已儲存。')
            if announce:
                self.app.notify('語音設定已儲存。', owner=self)
            self.refresh_setting_sources()
            self.update_controls()
            return True
        except ValueError:
            self.status.configure(text='請選有效音色與語速；句尾須為 0～1500、段落須為 0～3000 的整數毫秒。')
            return False
        except ProjectError as error:
            self.status.configure(text=str(error))
            return False

    def refresh_voices(self):
        if self.job or self.provider_name() != 'edge-tts':
            return
        self.job, self.kind = self.flow.start_voice_refresh(), 'catalog'
        self.status.configure(text='正在取得線上音色清單…')
        self.schedule()

    def preview(self):
        if self.job or not self.batch_id:
            return
        if self.provider_name()!='kokoro' and not self.consent.get():
            self.status.configure(text='請先勾選同意將試聽文字傳送至線上語音服務。')
            return
        value = self.prepare_text()
        if not value.strip() or len(value) > 3000:
            self.status.configure(text='請輸入 1～3,000 字元後再試聽。')
            return
        if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
            self.status.configure(text='主視窗的書籍或批次已切換；請關閉本視窗後重新開啟。')
            return
        try:
            value_settings = self.current_settings()
            self.stop()
            self.job = self.flow.start_voice_preview(self.batch_id, text=value, start=0, end=len(value),
                                                      settings_override=value_settings)
            self.kind = 'preview'
            self.status.configure(text='正在產生試聽…可繼續在主視窗校對，或取消。')
            self.schedule()
        except (ProjectError, ValueError) as error:
            self.status.configure(text=str(error) if isinstance(error, ProjectError) else '請輸入有效的整數毫秒。')

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.update_controls()
        self.timer = self.after(100, self.poll)

    def poll(self):
        self.timer = None
        if self.job is not None:
            if not self.job.wait(0):
                if self.kind=='preview' and self.provider_name()=='kokoro':
                    self.status.configure(text=self.flow.local_voice_status()['phase']+'…可取消。')
                self.schedule()
                return
            state = self.job.state
            try:
                if self.kind == 'preview':
                    if state['status'] == 'completed':
                        self.flow.finish_voice_preview(self.job)
                    else:
                        self.flow.discard_voice_preview(self.job)
                self.job = None
                self.load_catalog()
                self.load_result()
                self.status.configure(text='試聽已產生。' if state['status'] == 'completed' and self.kind == 'preview'
                                      else '音色清單已更新；請明確選擇音色。' if state['status'] == 'completed'
                                      else '已取消；上一份成功結果保留。' if state['status'] == 'cancelled' else state['error'])
                if state['status'] == 'completed' and self.kind == 'preview' and not self.closing and self.winfo_ismapped():
                    self.play()
                if not self.closing:
                    self.app.notify(self.status.cget('text'), owner=self,
                                    kind='success' if state['status'] == 'completed' else
                                    'info' if state['status'] == 'cancelled' else 'error')
            except ProjectError as error:
                self.status.configure(text=str(error) + ' 可重試儲存，或關閉並捨棄本次結果。')
                self.closing = False
        try:
            if self.player.playing():
                self.schedule()
                return
            if self.status.cget('text') == PLAYING_PREVIEW:
                self.status.configure(text='試聽播放完畢。')
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.stop()
        self.update_controls()
        if self.closing and self.job is None:
            self.release()

    def update_controls(self):
        busy = self.job is not None
        defaults = self.scope.get() == '全書預設'
        self.save_button.configure(text='儲存設定')
        self.apply_defaults_button.grid() if defaults else self.apply_defaults_button.grid_remove()
        self.apply_defaults_button.configure(state='disabled' if busy else 'normal')
        self.set_production_busy(self.app.production.busy_for(self.flow))
        for control in (self.refresh_button, self.save_button):
            control.configure(state='disabled' if busy else 'normal')
        self.scope_control.configure(state='disabled' if busy else 'readonly')
        self.rate_control.configure(state='disabled' if busy else 'readonly')
        self.service_control.configure(state='disabled' if busy else 'readonly')
        self.model_control.configure(state='disabled' if busy or self.service_ids.get(self.service.get()) in ('edge-tts','kokoro') else 'normal')
        self.manage_button.configure(state='disabled' if busy else 'normal')
        self.rhythm_control.configure(state='disabled' if busy else 'readonly')
        for spinbox in (self.sentence_control, self.paragraph_control):
            spinbox.configure(state='disabled' if busy else 'normal')
        local_ready=self.service_ids.get(self.service.get())!='kokoro' or bool(self.flow.local_voice_packages())
        self.preview_button.configure(state='normal' if not busy and self.batch_id and local_ready else 'disabled')
        self.cancel_button.configure(state='normal' if busy else 'disabled')
        self.produce_button.configure(state='disabled' if busy else 'normal')
        self.settings_edited()
        self.source_control.configure(state='disabled' if busy else 'readonly')
        self.source_button.configure(state='disabled' if busy or not self.setting_sources else 'normal')
        self.produce_button.grid_remove() if defaults else self.produce_button.grid()
        self.voice_entry.configure(state='disabled' if busy else 'normal')
        self.voice_control.configure(state='disabled' if busy else 'normal')
        self.filter.configure(state='disabled' if busy else 'readonly')
        if busy:
            self.cancel_button.grid()
            self.progress.grid()
            self.progress.start(12)
            self.result_info.grid_remove()
        else:
            self.cancel_button.grid_remove()
            self.progress.stop()
            self.progress.grid_remove()
            if self.result_info.cget('text'):
                self.result_info.grid()
        self.set_production_busy(self.app.production.busy_for(self.flow))

    def set_production_busy(self, busy):
        self.apply_defaults_button.configure(state='disabled' if busy or self.job is not None else 'normal')
        if busy:
            for control in (self.save_button, self.source_button, self.produce_button):
                control.configure(state='disabled')
        elif hasattr(self, 'edit_traces'):
            self.save_button.configure(state='disabled' if self.job else 'normal')
            self.source_button.configure(state='disabled' if self.job or not self.setting_sources else 'normal')
            self.settings_edited()

    def load_result(self):
        try:
            preview = self.flow.voice_preview(self.batch_id) if self.batch_id else None
            self.play_button.configure(state='normal' if preview else 'disabled')
            if preview:
                value = preview['settings']
                self.result_info.configure(text=f'上次成功：{value["voice"]} · {len(preview["text"])} 字元（可能與目前設定不同）')
                self.result_info.grid()
            else:
                self.result_info.configure(text='')
                self.result_info.grid_remove()
        except ProjectError as error:
            self.result_info.configure(text=str(error))
            self.result_info.grid()
            self.play_button.configure(state='disabled')

    def play(self):
        try:
            self.player.play(self.flow.voice_preview_path(self.batch_id))
            self.status.configure(text=PLAYING_PREVIEW)
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def stop(self):
        try:
            self.player.stop()
            if self.status.cget('text') == PLAYING_PREVIEW:
                self.status.configure(text='已停止播放；上次成功試聽保留。')
        except ProjectError as error:
            self.status.configure(text=str(error))

    def cancel(self):
        if self.job is not None:
            if self.job.wait(0) and self.kind == 'preview' and self.job.state['status'] == 'completed':
                self.poll()
                return
            self.job.cancel()
            self.status.configure(text='取消中，正在釋放連線與音訊資源…')

    def close(self):
        self.stop()
        if self.job is not None:
            if not self.job.wait(0):
                self.closing = True
                self.cancel()
                self.schedule()
                return
            if self.kind == 'preview':
                if not messagebox.askyesno('捨棄本次試聽', '關閉並捨棄本次尚未保存的試聽？上一份成功結果保留。', parent=self):
                    return False
                self.flow.discard_voice_preview(self.job)
            self.job = None
        self.release()
        return True

    def release(self):
        self.stop()
        for variable, token in getattr(self, 'edit_traces', []):
            variable.trace_remove('write', token)
        for variable, token in self.rhythm_traces:
            variable.trace_remove('write', token)
        self.rhythm_traces.clear()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        if self.app.voice_dialog is self:
            self.app.voice_dialog = None
        if self.app.production.current is self:
            self.app.production.current = None
        self.app.shell.unregister(self)
        self.destroy()
