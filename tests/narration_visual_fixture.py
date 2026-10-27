"""Show real native narration controls against the synthetic acceptance project."""
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

root, app = make_app()
app.flow = ProjectWorkflow.open('.scratch/T10-real/book')
app.batch_id = app.flow.state['batches'][0]['id']
app.refresh()
root.geometry('1040x640+20+20')
app.voice_settings()
app.voice_dialog.geometry('740x650+40+40')
app.narration()
app.narration_dialog.geometry('700x580+60+60')


def close():
    if app.narration_dialog:
        app.narration_dialog.close()
    if app.voice_dialog:
        app.voice_dialog.close()
    root.destroy()


root.after(180000, close)
root.mainloop()
