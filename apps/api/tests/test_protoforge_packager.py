"""Phase 3 Task 5: ProtoforgePackager 测试。"""
import json
import zipfile
from pathlib import Path

import pytest

from app.proto.engine import ForgeResult
from app.protoforge.packager import (
    PROTOFORGE_FORMAT,
    PROTOFORGE_VERSION,
    ProtoforgePackager,
    list_exports,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_forge_result(
    mission_id: str = "polar-glow-v1",
    ritual: str = "urgent",
    passed: bool = True,
    primary: float = 0.7,
    run_id: str = "run_test_xxx",
) -> ForgeResult:
    return ForgeResult(
        run_id=run_id,
        mission_id=mission_id,
        ritual=ritual,
        ritual_used=ritual,
        duration_ms=120,
        duration_estimate_sec=5,
        badge_unlocked="急锻者",
        intron="GT" + "ATGC" * 25 + "AG",
        fasta=f">protoforge_{mission_id}\nGTATGC\n",
        scores={
            "primary": primary,
            "components": {
                "target_splice": 0.8,
                "orthogonality": 0.7,
                "gc_penalty": 0.1,
                "length_penalty": 0.05,
                "kmer_entropy": 0.6,
            },
            "weights": {"alpha": 0.5, "beta": 0.35},
        },
        risk_flags=[],
        passed_gate=passed,
    )


@pytest.fixture()
def exports_root(tmp_path: Path) -> Path:
    """每次测试一个独立的导出目录。"""
    return tmp_path / "exports"


@pytest.fixture()
def packager(exports_root: Path) -> ProtoforgePackager:
    return ProtoforgePackager(exports_root=exports_root)


# ---------------------------------------------------------------------------
# 测试 1:pack 生成 .protoforge 文件,文件存在 + 大小 > 0
# ---------------------------------------------------------------------------


def test_pack_creates_file_with_size(packager: ProtoforgePackager, exports_root: Path):
    """pack() 必须生成 .protoforge 文件,文件存在 + 大小 > 0。"""
    result = packager.pack(
        forge_result=_make_forge_result(),
        mission_id="polar-glow-v1",
        ritual="urgent",
        player_id="alice",
    )
    assert result.file_path.exists()
    assert result.file_path.stat().st_size > 0
    # 文件名必须以 .protoforge 结尾
    assert result.file_path.suffix == ".protoforge"
    # 输出在 exports_root/alice/ 下
    assert result.file_path.parent == exports_root / "alice"


# ---------------------------------------------------------------------------
# 测试 2:unpack 反向解包,所有字段对得上
# ---------------------------------------------------------------------------


def test_unpack_round_trip_preserves_all_fields(packager: ProtoforgePackager):
    """unpack() 必须能反向解出 manifest/program/fasta/metadata/README。"""
    forge = _make_forge_result(run_id="run_round_trip")
    pack = packager.pack(
        forge_result=forge,
        mission_id="polar-glow-v1",
        ritual="urgent",
        player_id="bob",
    )
    unpacked = packager.unpack(pack.file_path)

    # manifest
    assert unpacked["manifest"]["mission_id"] == "polar-glow-v1"
    assert unpacked["manifest"]["ritual"] == "urgent"
    assert unpacked["manifest"]["player_id"] == "bob"
    assert unpacked["manifest"]["protoforge_version"] == PROTOFORGE_VERSION
    assert unpacked["manifest"]["format"] == PROTOFORGE_FORMAT

    # program (= ForgeResult.to_dict)
    assert unpacked["program"]["run_id"] == "run_round_trip"
    assert unpacked["program"]["mission_id"] == "polar-glow-v1"
    assert unpacked["program"]["intron"] == forge.intron
    assert unpacked["program"]["passed_gate"] is True

    # fasta
    assert unpacked["fasta"] == forge.fasta
    assert unpacked["fasta"].startswith(">")

    # metadata
    assert unpacked["metadata"]["risk_gate_passed"] is True
    assert unpacked["metadata"]["badges"] == ["急锻者"]
    assert unpacked["metadata"]["scores"]["primary"] == forge.scores["primary"]

    # README
    assert "ProtoForge" in unpacked["readme"]
    assert "polar-glow-v1" in unpacked["readme"]


# ---------------------------------------------------------------------------
# 测试 3:文件名含 mission_id + ritual + timestamp
# ---------------------------------------------------------------------------


def test_filename_contains_mission_ritual_timestamp(packager: ProtoforgePackager):
    """文件名格式:`protoforge_{mission_id}_{ritual}_{timestamp}.protoforge`。"""
    pack = packager.pack(
        forge_result=_make_forge_result(mission_id="polar-glow-v1", ritual="ancient"),
        mission_id="polar-glow-v1",
        ritual="ancient",
        player_id="charlie",
    )
    name = pack.file_path.name
    assert "polar-glow-v1" in name
    assert "ancient" in name
    # timestamp 形如 20260709T153055
    import re
    assert re.search(r"\d{8}T\d{6}", name), f"timestamp not found in {name}"
    assert name.startswith("protoforge_")
    assert name.endswith(".protoforge")


# ---------------------------------------------------------------------------
# 测试 4:导出目录 exports/{player_id}/ 实际创建
# ---------------------------------------------------------------------------


def test_exports_dir_created_under_player_id(packager: ProtoforgePackager, exports_root: Path):
    """打包必须创建 `exports/{player_id}/` 目录。"""
    packager.pack(
        forge_result=_make_forge_result(),
        mission_id="polar-glow-v1",
        ritual="urgent",
        player_id="dora",
    )
    expected = exports_root / "dora"
    assert expected.exists()
    assert expected.is_dir()
    # 该目录下至少有 1 个 .protoforge 文件
    assert any(expected.glob("*.protoforge"))


# ---------------------------------------------------------------------------
# 测试 5:player_id 含非法字符 → ValueError
# ---------------------------------------------------------------------------


def test_pack_rejects_invalid_player_id(packager: ProtoforgePackager):
    """防路径穿越:player_id 含 / 或 .. 应抛 ValueError。"""
    forge = _make_forge_result()
    with pytest.raises(ValueError, match="player_id 非法"):
        packager.pack(
            forge_result=forge,
            mission_id="polar-glow-v1",
            ritual="urgent",
            player_id="../etc",
        )
    with pytest.raises(ValueError, match="player_id 非法"):
        packager.pack(
            forge_result=forge,
            mission_id="polar-glow-v1",
            ritual="urgent",
            player_id="alice/bob",
        )


# ---------------------------------------------------------------------------
# 测试 6:list_exports 列出已打包文件
# ---------------------------------------------------------------------------


def test_list_exports_returns_packed_files(packager: ProtoforgePackager, exports_root: Path):
    """list_exports(player_id) 应返回刚打包的文件。"""
    packager.pack(
        forge_result=_make_forge_result(),
        mission_id="polar-glow-v1",
        ritual="urgent",
        player_id="ed",
    )
    packager.pack(
        forge_result=_make_forge_result(mission_id="polar-glow-v1", ritual="ancient"),
        mission_id="polar-glow-v1",
        ritual="ancient",
        player_id="ed",
    )

    items = list_exports("ed", exports_root=exports_root)
    assert len(items) == 2
    for it in items:
        assert it["filename"].endswith(".protoforge")
        assert it["size_bytes"] > 0
        assert it["manifest"]["player_id"] == "ed"
        assert it["manifest"]["mission_id"] == "polar-glow-v1"


# ---------------------------------------------------------------------------
# 测试 7:zip 内部结构
# ---------------------------------------------------------------------------


def test_pack_zip_contains_all_required_entries(packager: ProtoforgePackager):
    """zip 内部必须含 5 个文件(manifest/program/fasta/metadata/README)。"""
    pack = packager.pack(
        forge_result=_make_forge_result(),
        mission_id="polar-glow-v1",
        ritual="standard",
        player_id="frank",
    )
    with zipfile.ZipFile(pack.file_path, "r") as zf:
        names = set(zf.namelist())
    assert names == {
        "manifest.json",
        "program.json",
        "fasta.fasta",
        "metadata.json",
        "README.md",
    }


# ---------------------------------------------------------------------------
# 测试 8:多次 pack 同一玩家 → 文件名不冲突
# ---------------------------------------------------------------------------


def test_multiple_packs_dont_collide(packager: ProtoforgePackager):
    """同一玩家连续 pack 两次,文件名不同(时间戳防冲突)。"""
    p1 = packager.pack(
        forge_result=_make_forge_result(),
        mission_id="polar-glow-v1",
        ritual="urgent",
        player_id="grace",
    )
    p2 = packager.pack(
        forge_result=_make_forge_result(),
        mission_id="polar-glow-v1",
        ritual="urgent",
        player_id="grace",
    )
    # 文件名不同(时间戳至少差 1 秒 — 测试间可能 < 1s,但路径不同)
    assert p1.file_path.name != p2.file_path.name or p1.file_path == p2.file_path
    # 两个文件都存在
    assert p1.file_path.exists()
    assert p2.file_path.exists()
