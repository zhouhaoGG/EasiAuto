import re
from pathlib import Path

# 全角标点映射表
PUNCT_MAP = {
    "，": ", ",
    "：": ": ",
    "！": "! ",
    "？": "? ",
    "；": "; ",
    "（": " (",
    "）": ") ",
}


def fix_punctuation(file_path: Path):
    content = file_path.read_text(encoding="utf-8")

    # 匹配 logger.xxx(...) 或 raise Exception(...)
    # 分组说明：1. 前缀(logger.xxx( 或 raise xxx() 2. 内容 3. 后缀())
    pattern = r"((?:logger\.\w+|raise\s+\w+)\()(.*?)(\))"

    def replace_puncts(match):
        prefix, body, suffix = match.groups()

        # 替换全角标点
        for char, replacement in PUNCT_MAP.items():
            body = body.replace(char, replacement)

        # 逻辑处理：清理多余空格并保证格式统一
        body = re.sub(r"\s+", " ", body).strip()

        # NOTE: 此处仅处理简单字符串内容，若包含复杂嵌套括号建议使用 AST 解析
        return f"{prefix}{body}{suffix}"

    new_content = re.sub(pattern, replace_puncts, content, flags=re.MULTILINE)

    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        print(f"Fixed: {file_path}")


def main():
    # 使用 pathlib 提升路径处理兼容性
    target_dir = Path(r"D:\MyPC\Advanced\Code\Python\Projects\EasiAuto\src")

    if not target_dir.exists():
        print(f"Error: Directory {target_dir} does not exist.")
        return

    for py_file in target_dir.rglob("*.py"):
        fix_punctuation(py_file)


if __name__ == "__main__":
    main()
