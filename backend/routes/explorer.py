from fastapi import APIRouter, Query, HTTPException
from pafrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/prfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path:from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    tfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPExcefrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/prfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_pafrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(targefrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.stafrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(stafrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(tfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get(from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_pafrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    iffrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue'from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.css', '.html',
        '.json', '.yafrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.css', '.html',
        '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.cfg', '.conf', '.log'from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.css', '.html',
        '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.cfg', '.conf', '.log',
        '.sh', '.bat', '.ps1', '.sql', '.javfrom fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.css', '.html',
        '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.cfg', '.conf', '.log',
        '.sh', '.bat', '.ps1', '.sql', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.css', '.html',
        '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.cfg', '.conf', '.log',
        '.sh', '.bat', '.ps1', '.sql', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.toml', '.gitignore', '.env', '.dockerfile', '.makefile',
from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os

router = APIRouter()

# 允许浏览的根目录白名单
ALLOWED_ROOTS = [
    Path("/mnt/d/project"),
    Path("/mnt/d"),
]

def _resolve_path(rel_path: str) -> Path:
    """安全解析路径，确保不越界"""
    target = Path(rel_path).resolve()
    # 允许无路径时返回根目录
    if not str(target).startswith("/mnt"):
        # 尝试在允许的根目录下查找
        for root in ALLOWED_ROOTS:
            candidate = root / rel_path
            if candidate.exists():
                return candidate
        raise HTTPException(status_code=403, detail="路径不在允许的范围内")
    # 确保在允许的根目录下
    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="路径不在允许的范围内")


@router.get("/list")
def list_directory(path: str = "/mnt/d/project"):
    """列出指定目录下的文件和文件夹"""
    target = _resolve_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # 跳过隐藏文件和 node_modules 等
            if entry.name.startswith('.') or entry.name in ('node_modules', '__pycache__', '.git'):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")

    # 返回父目录路径用于返回上一级
    parent = str(target.parent) if str(target) != str(target.parent) else None

    return {
        "path": str(target),
        "parent": parent,
        "items": items
    }


@router.get("/read")
def read_file(path: str = Query(..., description="文件绝对路径")):
    """读取文件内容（仅支持文本文件）"""
    target = _resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 限制文件大小 5MB
    if target.stat().st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，仅支持 5MB 以内的文件")

    # 仅允许文本类型
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.vue', '.jsx', '.tsx', '.css', '.html',
        '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.cfg', '.conf', '.log',
        '.sh', '.bat', '.ps1', '.sql', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.toml', '.gitignore', '.env', '.dockerfile', '.makefile',
    }
    if target.suffix.lower() not in text_extensions and target.name not in ('