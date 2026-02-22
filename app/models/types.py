from __future__ import annotations

from typing import Annotated, TypeAlias

from pydantic import StringConstraints

DirectoryId: TypeAlias = str
FileId: TypeAlias = str

# ファイル名・ディレクトリ名はパス区切り文字を含まない前提。
FileName: TypeAlias = Annotated[str, StringConstraints(min_length=1, pattern=r"^[^/\\]+$")]
DirectoryName: TypeAlias = Annotated[str, StringConstraints(min_length=1, pattern=r"^[^/\\]+$")]
