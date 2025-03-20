#!/usr/bin/env python3

with open('/app/Repos/mcp_arxiv_query/src/mcp_arxiv_query/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print(f"文件總行數: {len(lines)}")
    print(f"最後5行:")
    for i, line in enumerate(lines[-5:], start=len(lines)-4):
        print(f"{i}: {line}", end='')
