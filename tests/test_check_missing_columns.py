"""专栏失踪检测回归测试。

防止「agent 分支生成专栏后未合入 master 导致专栏失踪」问题复发。
参见 tests/bug_regression_list.md BUG-045。
"""
import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_check_missing_columns_script_exists():
    """脚本存在且可执行。"""
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'check_missing_columns.py')
    assert os.path.isfile(script), f"check_missing_columns.py 不存在: {script}"


def test_check_missing_columns_runs_clean():
    """脚本在当前仓库状态下运行应返回 0（无缺失）。

    若此测试失败，说明有专栏在远程分支上存在但 master 缺失，
    需要先找回再合并。这是防止专栏搞丢的回归断言。
    """
    result = subprocess.run(
        [sys.executable, 'scripts/check_missing_columns.py', '--strict'],
        capture_output=True, text=True, timeout=120,
        cwd=os.path.join(os.path.dirname(__file__), '..'),
    )
    assert result.returncode == 0, (
        f"专栏失踪检测发现缺失（exit={result.returncode}）:\n{result.stdout}\n{result.stderr}\n"
        f"请先按脚本输出的找回命令找回缺失专栏，再合并。"
    )


def test_check_missing_columns_decode_chinese_path():
    """脚本能正确解码 git 的八进制转义中文路径。"""
    from scripts.check_missing_columns import decode_git_path
    # 模拟 git ls-tree 输出的转义路径
    encoded = '"output/\350\257\264\350\257\235\344\271\213\351\201\223"'
    decoded = decode_git_path(encoded)
    assert decoded == '说话之道', f"解码失败: {decoded!r} != '说话之道'"
