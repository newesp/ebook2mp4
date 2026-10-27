"""Synthetic native visual fixture; stop file allows deterministic teardown."""
from pathlib import Path
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

root, app = make_app()
app.flow = ProjectWorkflow.open('.scratch/t09/real-book-final')
app.batch_id = app.flow.state['batches'][0]['id']
app.refresh()
root.geometry('1040x640+20+20')
app.voice_settings()
dialog = app.voice_dialog
dialog.geometry('740x650+60+35')


def watch():
    if Path('.scratch/t09/stop-visual').exists():
        if app.voice_dialog is not None:
            app.voice_dialog.close()
        root.destroy()
        return
    root.after(200, watch)


root.after(200, watch)
root.after(240000, root.destroy)
root.mainloop()
