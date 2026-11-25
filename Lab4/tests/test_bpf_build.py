"""Build the BPF object and check its BTF layout and sections (host, no root)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

XDP_DIR = Path(__file__).resolve().parents[1] / "xdp"
OBJ = XDP_DIR / "lab4_xdp.bpf.o"
TOOLS = ("clang", "bpftool", "llvm-objdump", "make")
EXPECTED_SIZES = {"tree_node": 24, "ids_config": 24, "flow_key": 16, "test_vec": 80,
                  "test_result": 16}

pytestmark = pytest.mark.skipif(
    any(shutil.which(t) is None for t in TOOLS), reason="clang/bpftool/llvm-objdump/make missing")


def run(*cmd: str) -> subprocess.CompletedProcess:
    """Runs a command, capturing merged output."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


@pytest.fixture(scope="module", name="built")
def built_fixture() -> subprocess.CompletedProcess:
    """Rebuilds the object from scratch."""
    run("make", "-C", str(XDP_DIR), "clean")
    return run("make", "-C", str(XDP_DIR))


def test_make_clean_build(built: subprocess.CompletedProcess) -> None:
    """make exits 0 and prints no warning."""
    assert built.returncode == 0, built.stderr
    assert "warning" not in (built.stdout + built.stderr).lower()
    assert OBJ.exists()


def test_struct_sizes(built: subprocess.CompletedProcess) -> None:
    """BTF sizes of the shared structs equal the contract."""
    assert built.returncode == 0
    out = run("bpftool", "btf", "dump", "file", str(OBJ)).stdout
    for name, size in EXPECTED_SIZES.items():
        match = re.search(rf"STRUCT '{name}' size=(\d+)", out)
        assert match and int(match.group(1)) == size, name


def test_xdp_sections(built: subprocess.CompletedProcess) -> None:
    """The object has an xdp section (both programs use SEC("xdp"))."""
    assert built.returncode == 0
    assert re.search(r"\bxdp\b", run("llvm-objdump", "-h", str(OBJ)).stdout)
    syms = run("llvm-objdump", "-t", str(OBJ)).stdout
    assert "xdp_ids" in syms and "classify_test" in syms
