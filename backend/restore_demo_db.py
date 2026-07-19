"""
演示数据恢复脚本
当chat_demo.db被其他人覆盖时，执行此脚本可恢复演示数据

使用方法：
    cd backend
    python restore_demo_db.py
"""
import os, shutil, sys
from datetime import datetime

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backup")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_demo.db")

def main():
    # 查找最新的备份文件
    if not os.path.exists(BACKUP_DIR):
        print(f"错误: 备份目录不存在: {BACKUP_DIR}")
        return

    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")])
    if not backups:
        print("错误: 没有找到备份文件")
        return

    latest = backups[-1]
    backup_path = os.path.join(BACKUP_DIR, latest)

    # 先备份当前db（以防万一）
    if os.path.exists(DB_PATH):
        current_backup = os.path.join(BACKUP_DIR, f"chat_demo_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, current_backup)
        print(f"已备份当前db到: {current_backup}")

    # 恢复
    shutil.copy2(backup_path, DB_PATH)
    print(f"\n✓ 已恢复演示数据")
    print(f"  来源: {backup_path}")
    print(f"  目标: {DB_PATH}")
    print(f"\n请重启后端服务以加载恢复的数据")

if __name__ == "__main__":
    main()
