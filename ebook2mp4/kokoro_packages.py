"""Trusted, optional offline voice packages. No project data lives here."""
import asyncio
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

from .workflow import ProjectError


def home():
    return Path(os.environ.get('EBOOK2MP4_KOKORO_HOME') or
                str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'ebook2mp4/kokoro'))


@lru_cache(maxsize=1)
def release():
    try:
        return json.loads(Path(__file__).with_name('kokoro_release.json').read_bytes())
    except (OSError,ValueError):
        raise ProjectError('缺少本機語音包版本清單，請重新安裝完整主程式。') from None


class PackageLease:
    """An OS file lock survives thread changes and is released on process death."""
    def __init__(self):
        import msvcrt
        home().mkdir(parents=True,exist_ok=True)
        self.stream=(home()/'.engine.lock').open('a+b')
        if self.stream.seek(0,2)==0:self.stream.write(b'0');self.stream.flush()
        self.stream.seek(0)
        try:msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.stream.close()
            raise ProjectError('本機語音包正在使用或安裝中，請先停止其他視窗的工作。') from None

    def close(self):
        self.stream.close()


def package(identity):
    expected=release()
    if identity!=expected['id']:
        raise ProjectError('缺少此版本的本機語音包，請匯入對應版本；不會改用其他模型。')
    folder=home()/identity
    try:
        marker=folder/'package.json';attributes=marker.stat()
        if folder.is_symlink() or folder.is_junction() or not _receipt_matches(str(marker),attributes.st_mtime_ns,attributes.st_size):
            raise ValueError()
    except (OSError,ValueError):
        raise ProjectError('本機語音包缺少或損毀，請重新匯入完整語音包。') from None
    return folder,expected


@lru_cache(maxsize=8)
def _receipt_matches(path,modified,size):
    return json.loads(Path(path).read_bytes())==release()


def catalog():
    try:
        folder,metadata=package(release()['id'])
        return [dict(id=metadata['id'],model=metadata['model'],voices=deepcopy(metadata['voices']),
                     bytes=sum(x['bytes'] for x in metadata['files']),path=str(folder))]
    except ProjectError:return []


async def verify(folder,metadata,*,runtime_only=False,progress=None):
    root=folder.resolve();parents=set()
    # Check the executable entrypoint before the large inventory, so re-import
    # can repair a broken worker without first scanning every dependency.
    entries=sorted(metadata['files'],key=lambda entry:entry['path']!='worker.py')
    if runtime_only:
        language=('kokoro/','misaki/','opencc/','cn2an/','pypinyin/','pypinyin_dict/',
                  'jieba/','en_core_web_sm/','espeakng_loader/')
        prefixes=tuple('runtime/Lib/site-packages/'+name for name in language)
        entries=[e for e in entries if e['path'].startswith(('model/',*prefixes))
                 or e['path']=='worker.py' or Path(e['path']).suffix.lower() in ('.dll','.pyd','.exe')]
    for index,entry in enumerate(entries):
        if progress and index%200==0:progress(index,len(entries))
        target=folder/entry['path']
        # Resolve each directory once, rather than issuing tens of thousands of
        # Windows final-path queries for sibling files in the same directory.
        if target.parent not in parents:
            if not target.parent.resolve().is_relative_to(root):
                raise ProjectError('語音包路徑無效，請重新匯入。')
            parents.add(target.parent)
        if target.is_symlink() or not target.absolute().is_relative_to(folder.absolute()):
            raise ProjectError('語音包路徑無效，請重新匯入。')
        try:
            with target.open('rb') as source:
                digest=hashlib.sha256()
                while data:=source.read(1024*1024):
                    digest.update(data);await asyncio.sleep(0)
            if target.stat().st_size!=entry['bytes'] or digest.hexdigest()!=entry['sha256']:raise ValueError()
        except (OSError,ValueError):
            raise ProjectError(f'語音包檔案缺少或校驗失敗：{entry["path"]}。請重新匯入完整語音包。') from None


async def install(archive):
    from .kokoro_runtime import engine
    engine().stop_if_idle()
    lease=PackageLease()
    try:
        metadata=release()
        with zipfile.ZipFile(archive) as source:
            entries=source.infolist()
            names=[e.filename for e in entries]
            required={e['path'] for e in metadata['files']}|{'package.json'}
            if len(set(names))!=len(names) or set(names)!=required:raise ValueError()
            for entry in entries:
                path=PurePosixPath(entry.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename
                        or stat.S_IFMT(entry.external_attr>>16) not in (0,stat.S_IFREG)):
                    raise ValueError()
            if source.getinfo('package.json').file_size>16_000_000:raise ValueError()
            if json.loads(source.read('package.json'))!=metadata:raise ValueError()
            for entry in metadata['files']:
                if source.getinfo(entry['path']).file_size!=entry['bytes']:raise ValueError()
            target=home()/metadata['id']
            if target.exists():
                if target.is_symlink() or target.is_junction():
                    raise ProjectError('語音包位置包含外部連結，請先移除該連結再匯入。')
                try:
                    await verify(target,metadata)
                    return metadata['id']
                except ProjectError:
                    pass  # Stage a complete replacement before touching the damaged installation.
            if shutil.disk_usage(home()).free < sum(e['bytes'] for e in metadata['files'])+25_000_000:
                raise ProjectError('磁碟空間不足，請釋放空間後重新匯入語音包。')
            with tempfile.TemporaryDirectory(prefix='.install-',dir=home()) as temporary:
                folder=Path(temporary)/'package';folder.mkdir()
                for entry in metadata['files']:
                    output=folder/entry['path'];output.parent.mkdir(parents=True,exist_ok=True)
                    digest=hashlib.sha256()
                    with source.open(entry['path']) as incoming,output.open('wb') as outgoing:
                        while data:=incoming.read(1024*1024):
                            digest.update(data);outgoing.write(data);await asyncio.sleep(0)
                    if digest.hexdigest()!=entry['sha256']:raise ValueError()
                (folder/'package.json').write_text(json.dumps(metadata,ensure_ascii=False,sort_keys=True),encoding='utf-8')
                backup=Path(temporary)/'old'
                if target.exists():target.replace(backup)
                try:folder.replace(target)
                except BaseException:
                    if backup.exists():backup.replace(target)
                    raise
            return metadata['id']
    except ProjectError:raise
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,RuntimeError):
        raise ProjectError('語音包損毀、不完整或版本不相容。請重新下載與本程式相符的完整語音包。') from None
    finally:lease.close()


def remove(identity):
    from .kokoro_runtime import engine
    folder,_=package(identity)
    engine().stop_if_idle()
    lease=PackageLease()
    try:
        if folder.resolve().parent!=home().resolve():raise ProjectError('語音包安裝位置無效，無法移除。')
        shutil.rmtree(folder)
    except OSError:raise ProjectError('語音包檔案仍被占用，請關閉其他程式後重試移除。') from None
    finally:lease.close()
