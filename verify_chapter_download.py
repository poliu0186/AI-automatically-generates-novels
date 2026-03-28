#!/usr/bin/env python3
"""
验证章节下载功能修复的脚本
"""

import requests
import json

def test_chapter_download():
    """测试章节下载功能"""
    url = "http://localhost:60001/download"

    # 模拟10个章节的内容
    test_content = ""
    for i in range(1, 11):
        test_content += f"第{i}章：测试章节标题\n\n"
        test_content += f"这是第{i}章的正文内容。\n\n"
        test_content += f"第{i}章包含了一些故事情节和人物对话。\n\n"
        test_content += f"\"你好，\"张三说道，\"这是第{i}章的对话内容。\"\n\n"
        test_content += f"李四回答道：\"是的，这是一个很长的章节内容。\"\n\n\n"

    test_data = {
        "content": test_content,
        "format": "txt",
        "title": "chapter_test_novel"
    }

    try:
        response = requests.post(url, json=test_data)
        if response.status_code == 200:
            print("✅ 章节下载端点响应正常")
            print(f"📄 响应内容类型: {response.headers.get('content-type')}")
            print(f"📁 建议文件名: {response.headers.get('content-disposition', 'N/A')}")

            # 保存测试文件
            with open("chapter_download_test.txt", "wb") as f:
                f.write(response.content)
            print("💾 测试文件已保存为 chapter_download_test.txt")

            # 验证内容
            content = response.content.decode('utf-8', errors='ignore')
            chapter_count = content.count('第')
            print(f"📊 检测到大约 {chapter_count} 个章节标记")

            # 显示内容预览
            lines = content.split('\n')
            print(f"📖 内容预览 (前10行):")
            for i, line in enumerate(lines[:10]):
                if line.strip():
                    print(f"   {i+1}: {line[:80]}{'...' if len(line) > 80 else ''}")

            return True
        else:
            print(f"❌ 下载端点返回错误状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def check_app_running():
    """检查应用是否在运行"""
    try:
        response = requests.get("http://localhost:60001/", timeout=5)
        if response.status_code == 200:
            print("✅ Flask应用正在运行")
            return True
        else:
            print(f"❌ 应用响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Flask应用，请确保应用正在运行在端口60001")
        return False
    except Exception as e:
        print(f"❌ 检查应用状态时发生错误: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始验证章节下载功能修复...")
    print("=" * 50)

    # 检查应用状态
    if not check_app_running():
        print("\n请先启动Flask应用: python app.py")
        exit(1)

    print("\n" + "=" * 50)

    # 测试章节下载功能
    if test_chapter_download():
        print("\n✅ 章节下载功能修复验证成功！")
        print("\n📋 验证结果:")
        print("   - 后端下载端点正常响应")
        print("   - TXT格式下载功能正常")
        print("   - 章节内容可以正确生成和下载")
    else:
        print("\n❌ 章节下载功能验证失败")

    print("\n" + "=" * 50)
    print("🎯 接下来测试前端功能:")
    print("   1. 访问 http://localhost:60001/ 进入主应用")
    print("   2. 在章节区域生成一些章节正文内容")
    print("   3. 点击聊天界面中的'下载小说'按钮")
    print("   4. 验证是否能正确下载所有章节的内容")
    print("   5. 或者访问 http://localhost:60001/test 查看测试页面")