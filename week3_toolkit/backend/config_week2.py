# -*- coding: utf-8 -*-
"""
文件编号：config
所属周次：Week 2
实训步骤：训练配置中心
功能作用：集中管理 RAF-DB 训练、学生数据迁移学习、评估与预测所需路径和超参数。

说明：
1. 本文件默认放在 vision-prac/week2_toolkit/ 下。
2. 若项目根目录无法自动识别，可在 Windows CMD 中设置：
   set VISION_PRAC_ROOT=E:\\工程\\QQ工作文件下载\\2026春 上课\\[20252011]视觉模型应用开发13-16周\\vision-prac
3. 训练默认使用轻量 CNN，适合 RTX 2060 6GB 和课堂演示。
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import List


# -----------------------------------------------------------------------------
# 1. 项目路径
# -----------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
TOOLKIT_DIR = THIS_FILE.parent


def _guess_project_root() -> Path:
    env_root = os.environ.get("VISION_PRAC_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    # 常规位置：vision-prac/week2_toolkit/config_week2.py
    parent = TOOLKIT_DIR.parent
    if (parent / "RAF-DB").exists() or (parent / "data").exists():
        return parent.resolve()

    # 兼容把工具包临时放到 Yolo/、week1_toolkit/ 或其他子目录的情况
    for p in [TOOLKIT_DIR] + list(TOOLKIT_DIR.parents):
        if (p / "RAF-DB").exists() and (p / "data").exists():
            return p.resolve()
    return parent.resolve()


PROJECT_ROOT = _guess_project_root()
DATA_DIR = PROJECT_ROOT / "data"
RAF_DB_DIR = PROJECT_ROOT / "RAF-DB"
WEEK1_OUTPUT_DIR = DATA_DIR / "week1_output"
WEEK2_OUTPUT_DIR = DATA_DIR / "week2_output"

# Week2 输出分区
PREPARED_RAFDB_DIR = WEEK2_OUTPUT_DIR / "01_rafdb_prepared"
RAFDB_TRAIN_DIR = WEEK2_OUTPUT_DIR / "02_rafdb_train"
STUDENT_PREPARED_DIR = WEEK2_OUTPUT_DIR / "03_student_prepared"
STUDENT_FINETUNE_DIR = WEEK2_OUTPUT_DIR / "04_student_finetune"
EVAL_OUTPUT_DIR = WEEK2_OUTPUT_DIR / "05_evaluate"
PREDICT_OUTPUT_DIR = WEEK2_OUTPUT_DIR / "06_predict"
FIGURE_OUTPUT_DIR = WEEK2_OUTPUT_DIR / "07_figures"

# Week1 默认可衔接数据集目录
WEEK1_DATASET_DIR = WEEK1_OUTPUT_DIR / "05_dataset"


# -----------------------------------------------------------------------------
# 2. 表情类别
# -----------------------------------------------------------------------------
EMOTION_CLASSES = [
    "anger",
    "disgust",
    "fear",
    "happiness",
    "sadness",
    "surprise",
    "neutral",
]

EMOTION_CN = {
    "anger": "生气",
    "disgust": "厌恶",
    "fear": "恐惧",
    "happiness": "高兴",
    "sadness": "悲伤",
    "surprise": "惊讶",
    "neutral": "中性",
}

CLASS_TO_ID = {name: idx for idx, name in enumerate(EMOTION_CLASSES)}
ID_TO_CLASS = {idx: name for name, idx in CLASS_TO_ID.items()}

# RAF-DB 常见标注为 1~7；本工具包会自动识别 0~6 或 1~7。
RAFDB_LABEL_MODE = "zero_based"  # auto / zero_based / one_based

# 兼容数字文件夹、英文文件夹、中文文件夹
FOLDER_NAME_TO_CLASS = {
    "0": "anger",
    "1": "disgust",
    "2": "fear",
    "3": "happiness",
    "4": "sadness",
    "5": "surprise",
    "6": "neutral",
    "anger": "anger",
    "angry": "anger",
    "生气": "anger",
    "disgust": "disgust",
    "厌恶": "disgust",
    "fear": "fear",
    "scared": "fear",
    "恐惧": "fear",
    "happiness": "happiness",
    "happy": "happiness",
    "joy": "happiness",
    "高兴": "happiness",
    "开心": "happiness",
    "sadness": "sadness",
    "sad": "sadness",
    "悲伤": "sadness",
    "surprise": "surprise",
    "surprised": "surprise",
    "惊讶": "surprise",
    "neutral": "neutral",
    "normal": "neutral",
    "中性": "neutral",
    "自然": "neutral",
}


# -----------------------------------------------------------------------------
# 3. 训练超参数
# -----------------------------------------------------------------------------
RANDOM_SEED = 2026
IMAGE_SIZE = 112
BATCH_SIZE = 32
NUM_WORKERS = 0  # Windows + PyCharm 课堂环境建议设为 0，避免多进程卡住
EPOCHS_RAFDB = 20
EPOCHS_FINETUNE = 10
LEARNING_RATE = 1e-3
FINETUNE_LR = 1e-4
WEIGHT_DECAY = 1e-4
VAL_RATIO_WHEN_NEEDED = 0.20
TEST_RATIO_WHEN_NEEDED = 0.10
EARLY_STOP_PATIENCE = 6
USE_CLASS_WEIGHT = True
USE_AMP = True

# 默认模型：emotion_cnn 训练快，适合课堂；可选 simple_resnet18、mobilenet_v2。
DEFAULT_MODEL_NAME = "resnet50"


# -----------------------------------------------------------------------------
# 4. 文件类型
# -----------------------------------------------------------------------------
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TEXT_SUFFIXES = {".txt", ".csv"}


# -----------------------------------------------------------------------------
# 5. 通用工具函数
# -----------------------------------------------------------------------------
def ensure_week2_dirs() -> None:
    for p in [
        DATA_DIR,
        WEEK2_OUTPUT_DIR,
        PREPARED_RAFDB_DIR,
        RAFDB_TRAIN_DIR,
        STUDENT_PREPARED_DIR,
        STUDENT_FINETUNE_DIR,
        EVAL_OUTPUT_DIR,
        PREDICT_OUTPUT_DIR,
        FIGURE_OUTPUT_DIR,
    ]:
        Path(p).mkdir(parents=True, exist_ok=True)


def list_images(root: Path) -> List[Path]:
    root = Path(root)
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES])


def list_texts(root: Path) -> List[Path]:
    root = Path(root)
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES])


def load_module(file_name: str):
    module_path = TOOLKIT_DIR / file_name
    spec = importlib.util.spec_from_file_location(Path(file_name).stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def print_config_summary() -> None:
    print("\n[Week2 配置摘要]")
    print(f"  项目根目录       : {PROJECT_ROOT}")
    print(f"  RAF-DB 目录      : {RAF_DB_DIR}")
    print(f"  Week1 数据集目录 : {WEEK1_DATASET_DIR}")
    print(f"  Week2 输出目录   : {WEEK2_OUTPUT_DIR}")
    print(f"  表情类别         : {', '.join(EMOTION_CLASSES)}")
    print(f"  默认图像尺寸     : {IMAGE_SIZE}")
    print(f"  默认模型         : {DEFAULT_MODEL_NAME}")
    print(f"  默认 batch size  : {BATCH_SIZE}")
    print(f"  默认 num_workers : {NUM_WORKERS}")


if __name__ == "__main__":
    ensure_week2_dirs()
    print_config_summary()
