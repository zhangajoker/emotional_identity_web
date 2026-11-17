import io
import cv2
import torch
import numpy as np
import tempfile
import os
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from torchvision import transforms, models
import torch.nn as nn
import pymysql
from pydantic import BaseModel
from dotenv import load_dotenv

class DiaryEntry(BaseModel):
    visual_emotion: str
    confidence: float
    text_content: str
    healing_message: str

load_dotenv()

def get_db_config():
    return {
        # os.environ.get('变量名', '默认值')
        'host': os.environ.get('DB_HOST', 'db'),          # 默认用 Docker 的 db
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', '314159'),
        'database': os.environ.get('DB_NAME', 'emotion_db'), # 默认用 Docker 的 emotion_db
        'charset': 'utf8mb4',
        'use_unicode': True,
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': True
    }

# ==========================================
# 1. 初始化 FastAPI 应用与跨域配置
# ==========================================
app = FastAPI(title="Emotion Healing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源跨域访问
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"✨ 正在使用计算设备: {device}")

# ==========================================
# 2. 模型加载与初始化
# ==========================================
# 加载 YOLOv8 人脸检测模型
FACE_MODEL_PATH = r"./model/yolo_face.pt"
print("📦 加载 YOLO 人脸模型中...")
face_detector = YOLO(FACE_MODEL_PATH)

# 加载 ResNet 表情分类模型
EMOTION_MODEL_PATH = r"./model/rafdb_emotion.pt"
print("📦 加载 ResNet 表情模型中...")

emotion_model = models.resnet50(weights=None)
num_ftrs = emotion_model.fc.in_features
emotion_model.fc = nn.Linear(num_ftrs, 7)

# 强制全部转为小写，完美对接前端
idx_to_emotion = {5: 'surprise', 2: 'fear', 1: 'disgust', 3: 'happiness', 4: 'sadness', 0: 'anger', 6: 'neutral'}

try:
    checkpoint = torch.load(EMOTION_MODEL_PATH, map_location=device)
    state_dict = checkpoint.get('model_state', checkpoint)
    state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
    emotion_model.load_state_dict(state_dict)

    if 'class_to_id' in checkpoint:
        idx_to_emotion = {v: k.lower() for k, v in checkpoint['class_to_id'].items()}
    print("✅ 表情模型加载成功！")
except Exception as e:
    print(f"❌ 警告: 模型加载异常: {e}")

emotion_model.to(device)
emotion_model.eval()

# 【核心修改 1】：由 224 修改为 112，严格匹配训练阶段的输入特征尺度
val_transform = transforms.Compose([
    transforms.Resize((112, 112)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# ==========================================
# 3.数据库配置与查询逻辑
# ==========================================
DB_CONFIG = {
    'host': 'db',  # 数据库地址
    'user': 'root',  # 【请替换】你的数据库用户名
    'password': '314159',  # 【请替换】你的数据库密码
    'database': 'emotion_db',  # 刚才创建的数据库名
    'charset': 'utf8mb4',
    'use_unicode': True
}


def get_random_message(emotion_label: str) -> str:
    """去数据库里根据情绪随机捞取一句话"""
    print(f"DEBUG: 正在尝试获取情绪 '{emotion_label}' 的语录...")

    # 动态获取当前环境的数据库配置
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            sql = "SELECT message FROM healing_messages WHERE emotion = %s"
            cursor.execute(sql, (emotion_label,))
            result = cursor.fetchone()

            if result:
                return result['message']
            return "心情不错，继续保持哦！"
    except Exception as e:
        print(f"❌ 数据库查询失败 (Host: {db_config['host']}, DB: {db_config['database']}): {e}")
        import traceback
        traceback.print_exc()
        return "数据库小憩中..."
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

#===========================================
#4.保存多情绪日记
#===========================================
@app.post("/api/diary")
async def save_diary(entry: DiaryEntry):
    print(f"DEBUG: 正在封存新的情绪日记... 情绪: {entry.visual_emotion}")

    db_config = get_db_config()
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # 插入到我们在第一阶段设计好的 diaries 表中
            sql = """
                  INSERT INTO diaries (visual_emotion, confidence, text_content, healing_message)
                  VALUES (%s, %s, %s, %s) \
                  """
            cursor.execute(sql, (
                entry.visual_emotion,
                entry.confidence,
                entry.text_content,
                entry.healing_message
            ))
        return {"status": "success", "message": "你的情绪已温柔封存"}

    except Exception as e:
        print(f"❌ 保存日记至数据库失败: {e}")
        # 向前端抛出标准的 500 服务器错误响应
        raise HTTPException(status_code=500, detail="系统在封存记忆时开小差了，请稍后再试。")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

# ==========================================
# 5. 获取历史日记列表
# ==========================================
@app.get("/api/diary/history")
async def get_diary_history():
    print("DEBUG: 正在调取历史情绪足迹...")

    db_config = get_db_config()
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # 1. 使用 DATE_FORMAT 格式化时间，更符合人类阅读习惯
            # 2. 按创建时间倒序（DESC），最新的日记排在最前面
            sql = """
                  SELECT id, \
                         visual_emotion, \
                         confidence, \
                         text_content, \
                         healing_message, \
                         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') as formatted_time
                  FROM diaries
                  ORDER BY created_at DESC \
                  """
            cursor.execute(sql)
            results = cursor.fetchall()

        return {
            "status": "success",
            "count": len(results),
            "data": results
        }

    except Exception as e:
        print(f"❌ 读取历史日记失败: {e}")
        raise HTTPException(status_code=500, detail="无法唤醒过去的回忆，请稍后再试。")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

# ==========================================
# 6. 核心接口：单张图片分析
# ==========================================
@app.post("/api/analyze")
async def analyze_emotion(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')

        # EXIF 矫正：防止手机竖拍照片横向加载
        image = ImageOps.exif_transpose(image)

        img_cv2 = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        h, w, _ = img_cv2.shape

        # 保持 0.2 阈值确保高召回
        results = face_detector.predict(img_cv2, conf=0.2, verbose=False)
        boxes = results[0].boxes

        if len(boxes) == 0:
            return {"status": "error", "message": "画面中似乎没有找到人脸哦，调整角度再试一次吧~"}

        x1, y1, x2, y2 = boxes[0].xyxy[0].cpu().numpy().astype(int)

        # 【核心修改 2】：移除 15% 的 Margin 外扩，回归与本地流水线完全对齐的紧凑人脸边框
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        face_img_cv2 = img_cv2[y1:y2, x1:x2]
        face_pil = Image.fromarray(cv2.cvtColor(face_img_cv2, cv2.COLOR_BGR2RGB))

        input_tensor = val_transform(face_pil).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = emotion_model(input_tensor)
            prob = torch.nn.functional.softmax(outputs[0], dim=0)
            score, preds = torch.max(prob, dim=0)
            emotion_idx = preds.item()
            confidence_pct = round(score.item() * 100, 1)

        final_emotion = idx_to_emotion.get(emotion_idx, 'neutral').lower()
        random_healing_msg = get_random_message(final_emotion)

        return {
            "status": "success",
            "data": {
                "emotion": final_emotion,
                "confidence": confidence_pct,
                "message": random_healing_msg,
                "face_box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 7. 新增接口：视频抽帧分析
# ==========================================
@app.post("/api/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    temp_video_path = None
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_video:
            temp_video.write(await file.read())
            temp_video_path = temp_video.name

        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            return {"status": "error", "message": "无法打开视频文件"}

        frame_skip = 10  # 每 10 帧分析一次
        frame_count = 0
        processed_results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % frame_skip != 0:
                continue

            img_cv2 = frame
            h, w, _ = img_cv2.shape

            results = face_detector.predict(img_cv2, conf=0.2, verbose=False)
            boxes = results[0].boxes

            if len(boxes) > 0:
                x1, y1, x2, y2 = boxes[0].xyxy[0].cpu().numpy().astype(int)

                # 【核心修改 3】：同步移除视频流接口中的 Margin 外扩，确保前后面部分割标准完全一致
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)

                face_img_cv2 = img_cv2[y1:y2, x1:x2]
                face_pil = Image.fromarray(cv2.cvtColor(face_img_cv2, cv2.COLOR_BGR2RGB))

                input_tensor = val_transform(face_pil).unsqueeze(0).to(device)
                with torch.no_grad():
                    outputs = emotion_model(input_tensor)
                    prob = torch.nn.functional.softmax(outputs[0], dim=0)
                    score, preds = torch.max(prob, dim=0)
                    emotion_idx = preds.item()
                    confidence_pct = round(score.item() * 100, 1)

                final_emotion = idx_to_emotion.get(emotion_idx, 'neutral').lower()
                random_healing_msg = get_random_message(final_emotion)
                processed_results.append({
                    "emotion": final_emotion,
                    "confidence": confidence_pct
                })

        cap.release()

        if not processed_results:
            return {"status": "error", "message": "视频中没有检测到清晰的人脸哦"}

        # 统计主导情绪和平均置信度
        emotions_list = [r["emotion"] for r in processed_results]
        dominant_emotion = max(set(emotions_list), key=emotions_list.count)
        avg_confidence = sum(r["confidence"] for r in processed_results) / len(processed_results)

        return {
            "status": "success",
            "data": {
                "dominant_emotion": dominant_emotion,
                "average_confidence": round(avg_confidence, 1),
                "message": random_healing_msg,
                "total_frames_analyzed": len(processed_results)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 确保清理掉临时视频文件
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except:
                pass