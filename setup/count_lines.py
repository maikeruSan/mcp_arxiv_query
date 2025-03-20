#!/usr/bin/env python3
import sys

def count_lines(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()
        print(f"文件總行數: {len(lines)}")
        print(f"最後10行:")
        for i, line in enumerate(lines[-10:], start=len(lines)-9):
            print(f"{i}: {line}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        count_lines(sys.argv[1])
    else:
        print("請提供檔案路徑")
