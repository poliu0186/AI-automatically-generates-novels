#!/usr/bin/env python3
"""
验证下载功能修复的脚本
"""

import requests
import json

def test_download_endpoint():
    """测试下载端点"""
    url = "http://localhost:60001/download"

    test_data = {
        "content": "第1章：开端\n\n这是一个测试章节的内容。\n\n第2章：发展\n\n故事继续发展。",
        "format": "txt",
        "title": "test_novel"
    }

    try:
        response = requests.post(url, json=test_data)
        if response.status_code == 200:
            print("✅ 下载端点响应正常")
            print(f"📄 响应内容类型: {response.headers.get('content-type')}")
            print(f"📁 建议文件名: {response.headers.get('content-disposition', 'N/A')}")
            print(f"📊 内容长度: {len(response.content)} 字节")

            # 保存测试文件
            with open("test_download_result.txt", "wb") as f:
                f.write(response.content)
            print("💾 测试文件已保存为 test_download_result.txt")

            # 显示内容预览
            content_preview = response.content.decode('utf-8', errors='ignore')[:200]
            print(f"📖 内容预览:\n{content_preview}...")

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
    print("🔍 开始验证小说下载功能修复...")
    print("=" * 50)

    # 检查应用状态
    if not check_app_running():
        print("\n请先启动Flask应用: python app.py")
        exit(1)

    print("\n" + "=" * 50)

    # 测试下载功能
    if test_download_endpoint():
        print("\n✅ 下载功能修复验证成功！")
        print("\n📋 验证结果:")
        print("   - 后端下载端点正常响应")
        print("   - TXT格式下载功能正常")
        print("   - 文件可以正确生成和下载")
    else:
        print("\n❌ 下载功能验证失败")

    print("\n" + "=" * 50)
    print("🎯 接下来测试前端功能:")
    print("   1. 访问 http://localhost:60001/test 查看测试页面")
    print("   2. 点击'添加10个章节的测试内容'按钮")
    print("   3. 点击'测试下载小说'按钮")
    print("   4. 验证是否能弹出下载对话框并成功下载")