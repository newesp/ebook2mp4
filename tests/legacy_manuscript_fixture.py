"""Exercise the retained legacy candidate adapters explicitly, outside main navigation.

Main-window acceptance lives in test_unified_manuscript. These older tests protect
the page/paragraph decision adapters used to read historical projects.
"""
from ebook2mp4.gemini_desktop import ReviewDialog, SettingsDialog
from ebook2mp4.pdf_desktop import PdfDialog


def install(app):
    def review(selected=False):
        if app.dirty:
            app.flow.save_draft(app.batch_id, app.current_text)
            app.saved_text = app.current_text
        start, end = 0, len(app.current_text)
        ranges = app.editor.tag_ranges('sel')
        if selected and ranges:
            start, end = [len(app.editor.get('1.0', index)) for index in ranges]
        job = app.flow.start_gemini_review(app.batch_id, start=start, end=end,
            script={'自動':'auto','繁體':'traditional','簡體':'simplified','保留原樣':'preserve'}[app.script.get()],
            punctuation=app.normalize_punctuation.get())
        app.gemini_dialog = ReviewDialog(app, job=job)
    def history():
        app.gemini_dialog = ReviewDialog(app)
    def settings():
        app.gemini_settings_dialog = SettingsDialog(app)
    def compare():
        app.pdf_dialog = PdfDialog(app, batch_id=app.batch_id)
    app.gemini_review = review
    app.gemini_history = history
    app.gemini_settings = settings
    app.compare_pdf_pages = compare
    app.gemini_all_button = type('LegacyAction', (), {'invoke': staticmethod(review)})()
    app.gemini_history_button = type('LegacyAction', (), {'invoke': staticmethod(history)})()
