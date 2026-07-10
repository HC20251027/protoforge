""".protoforge 文件打包器(Phase 3 Task 5)。

`.protoforge` 是 ProtoForge 玩家作品的存档格式:
- 本质:zip 压缩包,内含 manifest / program / fasta / metadata / README
- 用途:
  1. 通关后自动打包(本任务核心)
  2. 上传到 Steam Workshop(适配层在 `steam.py`)
  3. 玩家下载后用 `unpack()` 反向解包(本任务先实现,Phase 4 加 UI 加载)

**设计取舍**:
- 用 zip 而不是自研二进制格式 — Python stdlib `zipfile`,零依赖
- manifest 用 JSON 字段而非 zipfile comment — 方便 debug,玩家可以直接 unzip 看到内容
- 文件名:`protoforge_{mission_id}_{ritual}_{timestamp}.protoforge`
  - mission_id 含 "-" — 保留原样(win 文件系统允许)
  - timestamp 用 `%Y%m%dT%H%M%S` 形式(无冒号 — win 文件名禁用)
- 输出目录:`apps/api/data/exports/{player_id}/`(在项目内,不写 C 盘)
"""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.proto.engine import ForgeResult


# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

PROTOFORGE_VERSION = "0.1.0"  # .protoforge 文件格式版本
PROTOFORGE_FORMAT = "protoforge/zip"  # 人类可读标识
_PROTOFORGE_SUFFIX = ".protoforge"


@dataclass(frozen=True)
class PackResult:
    """打包结果(给调用方做后续处理用)。"""

    file_path: Path
    mission_id: str
    ritual: str
    player_id: str
    size_bytes: int


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------


def _default_exports_root() -> Path:
    """默认导出根目录:`<settings.data_dir>/exports/`(在项目内,不写 C 盘)。

    测试可通过 monkeypatch `settings.data_dir` 改到 tmp_path。
    """
    from app.config import settings  # 局部 import 避免循环依赖

    root = Path(settings.data_dir) / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _timestamp_str() -> str:
    """生成文件名友好的时间戳(`20260709T153055`)。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


# ---------------------------------------------------------------------------
# 主体:ProtoforgePackager
# ---------------------------------------------------------------------------


class ProtoforgePackager:
    """.protoforge 文件打包器。

    使用方式:
        packager = ProtoforgePackager()
        result = packager.pack(forge_result, mission_id="polar-glow-v1",
                               ritual="urgent", player_id="alice")
        # result.file_path → Path 对象
    """

    def __init__(self, exports_root: Optional[Path] = None) -> None:
        self._exports_root = Path(exports_root) if exports_root else _default_exports_root()
        self._exports_root.mkdir(parents=True, exist_ok=True)

    # ---------- 生成文件名 ----------

    def _build_filename(self, mission_id: str, ritual: str, timestamp: str) -> str:
        """生成文件名:`protoforge_{mission_id}_{ritual}_{timestamp}.protoforge`."""
        # 防止文件名里出现路径分隔符(虽然 mission_id 应当是安全的)
        safe_mission = mission_id.replace("/", "_").replace("\\", "_")
        safe_ritual = ritual.replace("/", "_").replace("\\", "_")
        return f"protoforge_{safe_mission}_{safe_ritual}_{timestamp}{_PROTOFORGE_SUFFIX}"

    # ---------- 内部:生成 manifest / metadata / README ----------

    @staticmethod
    def _build_manifest(
        mission_id: str,
        ritual: str,
        player_id: str,
        created_at: str,
        name: str,
    ) -> dict[str, Any]:
        return {
            "format": PROTOFORGE_FORMAT,
            "protoforge_version": PROTOFORGE_VERSION,
            "name": name,
            "mission_id": mission_id,
            "ritual": ritual,
            "player_id": player_id,
            "created_at": created_at,
        }

    @staticmethod
    def _forge_result_to_dict(result: ForgeResult) -> dict[str, Any]:
        """ForgeResult → dict(给 program.json 用)。"""
        return {
            "run_id": result.run_id,
            "mission_id": result.mission_id,
            "ritual": result.ritual,
            "ritual_used": result.ritual_used,
            "duration_ms": result.duration_ms,
            "duration_estimate_sec": result.duration_estimate_sec,
            "badge_unlocked": result.badge_unlocked,
            "intron": result.intron,
            "fasta": result.fasta,
            "scores": result.scores,
            "risk_flags": result.risk_flags,
            "passed_gate": result.passed_gate,
        }

    @staticmethod
    def _build_metadata(result: ForgeResult) -> dict[str, Any]:
        return {
            "scores": result.scores,
            "badges": [result.badge_unlocked] if result.badge_unlocked else [],
            "risk_gate_passed": result.passed_gate,
            "duration_estimate_sec": result.duration_estimate_sec,
        }

    @staticmethod
    def _build_readme(
        manifest: dict[str, Any],
        metadata: dict[str, Any],
        result_dict: dict[str, Any],
    ) -> str:
        """生成人类可读的 README.md。"""
        badge = manifest.get("ritual", "未知")
        primary = (metadata.get("scores") or {}).get("primary", 0.0)
        return (
            f"# {manifest['name']}\n\n"
            f"ProtoForge 玩家作品存档(.protoforge 格式 v{manifest['protoforge_version']})\n\n"
            f"## 基本信息\n\n"
            f"- 玩家 ID: `{manifest['player_id']}`\n"
            f"- 任务: `{manifest['mission_id']}`\n"
            f"- 仪式档位: **{badge}**\n"
            f"- 创作时间: {manifest['created_at']}\n"
            f"- Run ID: `{result_dict.get('run_id', 'n/a')}`\n\n"
            f"## 评分\n\n"
            f"- 综合得分: **{primary:.3f}**\n"
            f"- 风险门通过: {'✓ 是' if metadata.get('risk_gate_passed') else '✗ 否'}\n"
            f"- 预计耗时: {metadata.get('duration_estimate_sec', '?')}s\n\n"
            f"## 包含文件\n\n"
            f"- `manifest.json` — 文件清单与元信息\n"
            f"- `program.json` — 完整 ForgeResult(JSON)\n"
            f"- `fasta.fasta` — 内含子序列(FASTA 格式)\n"
            f"- `metadata.json` — 评分/徽章/风险门状态\n"
            f"- `README.md` — 本文件\n\n"
            f"---\n"
            f"由 ProtoForge Phase 3 生成(Steam Workshop 创意工坊格式)\n"
        )

    # ---------- 公开接口:pack / unpack ----------

    def pack(
        self,
        forge_result: ForgeResult,
        mission_id: str,
        ritual: str,
        player_id: str,
    ) -> PackResult:
        """打包 `.protoforge` 文件,返回 PackResult(file_path, ...)。

        Args:
            forge_result: run_forge 返回的 ForgeResult
            mission_id: 任务 ID
            ritual: 仪式档位("urgent" 等)
            player_id: 玩家 ID(子目录名,不能含路径分隔符)

        Returns:
            PackResult(file_path=..., size_bytes=...)

        Raises:
            ValueError: player_id 含非法字符(防止路径穿越)
        """
        # player_id 必须安全(防止路径穿越 — "../etc/passwd" 之类)
        if not player_id or not all(
            c.isalnum() or c in "_-." for c in player_id
        ):
            raise ValueError(
                f"player_id 非法(只允许字母数字 _-.): {player_id!r}"
            )

        # 1) 准备目录
        player_dir = self._exports_root / player_id
        player_dir.mkdir(parents=True, exist_ok=True)

        # 2) 文件名(含时间戳)
        timestamp = _timestamp_str()
        filename = self._build_filename(mission_id, ritual, timestamp)
        out_path = player_dir / filename

        # 3) 在内存里拼好所有内容(避免半写盘)
        created_at = datetime.now(timezone.utc).isoformat()
        manifest = self._build_manifest(
            mission_id=mission_id,
            ritual=ritual,
            player_id=player_id,
            created_at=created_at,
            name=filename.removesuffix(_PROTOFORGE_SUFFIX),
        )
        result_dict = self._forge_result_to_dict(forge_result)
        metadata = self._build_metadata(forge_result)
        readme = self._build_readme(manifest, metadata, result_dict)

        manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
        program_json = json.dumps(result_dict, ensure_ascii=False, indent=2)
        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

        # 4) 写到 zip(zipfile 写时建临时,结束后 move 替换)
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        try:
            with zipfile.ZipFile(
                tmp_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as zf:
                zf.writestr("manifest.json", manifest_json)
                zf.writestr("program.json", program_json)
                zf.writestr("fasta.fasta", forge_result.fasta)
                zf.writestr("metadata.json", metadata_json)
                zf.writestr("README.md", readme)
            tmp_path.replace(out_path)
        except Exception:
            # 半成品清理
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise

        return PackResult(
            file_path=out_path,
            mission_id=mission_id,
            ritual=ritual,
            player_id=player_id,
            size_bytes=out_path.stat().st_size,
        )

    def unpack(self, file_path: Path) -> dict[str, Any]:
        """反向解包 `.protoforge` 文件,返回 dict(zip 内所有内容)。

        Returns:
            {
                "manifest": dict,
                "program": dict,
                "fasta": str,
                "metadata": dict,
                "readme": str,
            }

        Raises:
            FileNotFoundError: 文件不存在
            zipfile.BadZipFile: 文件不是合法 zip
            KeyError: 缺少必填字段
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"protoforge file not found: {file_path}")

        with zipfile.ZipFile(file_path, "r") as zf:
            names = set(zf.namelist())
            required = {"manifest.json", "program.json", "fasta.fasta", "metadata.json", "README.md"}
            missing = required - names
            if missing:
                raise KeyError(
                    f"protoforge file missing required entries: {sorted(missing)}"
                )

            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            program = json.loads(zf.read("program.json").decode("utf-8"))
            fasta = zf.read("fasta.fasta").decode("utf-8")
            metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
            readme = zf.read("README.md").decode("utf-8")

        return {
            "manifest": manifest,
            "program": program,
            "fasta": fasta,
            "metadata": metadata,
            "readme": readme,
        }


# ---------------------------------------------------------------------------
# 公开工具:list_exports
# ---------------------------------------------------------------------------


def list_exports(
    player_id: str,
    exports_root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """列出某玩家已打包的 .protoforge 文件(给前端 /exports 页面用)。

    Returns:
        list of {filename, path, size_bytes, mtime, manifest}
    """
    root = Path(exports_root) if exports_root else _default_exports_root()
    if not player_id or not all(c.isalnum() or c in "_-." for c in player_id):
        return []
    player_dir = root / player_id
    if not player_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(player_dir.glob(f"*{_PROTOFORGE_SUFFIX}"), reverse=True):
        try:
            mtime = p.stat().st_mtime
            # 尝试读 manifest 头部(只读 1 个 entry,避免全 unzip)
            with zipfile.ZipFile(p, "r") as zf:
                try:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                except (KeyError, json.JSONDecodeError):
                    manifest = {}
            out.append(
                {
                    "filename": p.name,
                    "path": str(p),
                    "size_bytes": p.stat().st_size,
                    "mtime": mtime,
                    "manifest": manifest,
                }
            )
        except OSError:
            continue
    return out


__all__ = [
    "PROTOFORGE_VERSION",
    "PROTOFORGE_FORMAT",
    "PackResult",
    "ProtoforgePackager",
    "list_exports",
]
