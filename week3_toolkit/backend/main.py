import io
import cv2
import torch
import numpy as np
import os
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from torchvision import transforms, models
import torch.nn as nn
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import Depends
from pydantic import Field
from auth import get_current_user, router as auth_router
from db import get_connection, get_db_config
from social import router as social_router
from threading import BoundedSemaphore, Lock, Thread
from fastapi.concurrency import run_in_threadpool

#上传限制

from uploads import (
    ALLOWED_IMAGE_TYPES,
    ALLOWED_VIDEO_TYPES,
    MAX_ANALYZED_VIDEO_FRAMES,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_PIXELS,
    MAX_VIDEO_BYTES,
    MAX_VIDEO_SECONDS,
    read_upload_limited,
    save_video_upload_limited,
)

class DiaryEntry(BaseModel):
    visual_emotion: str = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=100)
    text_content: str = Field(min_length=1, max_length=10000)
    healing_message: str = Field(min_length=1, max_length=500)

load_dotenv()


# ==========================================
# 1. 初始化 FastAPI 应用与跨域配置
# ==========================================
app = FastAPI(title="Emotion Healing API")
app.include_router(auth_router)
app.include_router(social_router)

ai_chat_enabled = os.environ.get("ENABLE_AI_CHAT", "0") == "1"
if ai_chat_enabled:
    from chat import router as chat_router
    from chat_service import warm_up_chat_model

    app.include_router(chat_router)
    Thread(
        target=warm_up_chat_model,
        daemon=True,
    ).start()

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
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

#导入与全局锁
_inference_lock = Lock()
_video_job_slot = BoundedSemaphore(1)

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
# 3.查询逻辑
# ==========================================

def get_random_message(emotion_label: str) -> str:
    """去数据库里根据情绪随机捞取一句话"""
    print(f"DEBUG: 正在尝试获取情绪 '{emotion_label}' 的语录...")

    db_config = get_db_config()
    try:
        conn = get_connection()
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
async def save_diary(entry: DiaryEntry,
                     user:dict=Depends(get_current_user,)):
    print(f"DEBUG: 正在封存新的情绪日记... 情绪: {entry.visual_emotion}")

    db_config = get_db_config()
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 插入到我们在第一阶段设计好的 diaries 表中
            sql = """
                INSERT INTO diaries (
                    user_id,
                    visual_emotion,
                    confidence,
                    text_content,
                    healing_message
                )
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                user["id"],
                entry.visual_emotion,
                entry.confidence,
                entry.text_content,
                entry.healing_message,
            ))
        return {
            "status": "success",
            "diary_id": cursor.lastrowid,
            "message": "你的心情已温柔封存",
        }

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
async def get_diary_history(
    user: dict = Depends(get_current_user),):
    print("DEBUG: 正在调取历史情绪足迹...")

    db_config = get_db_config()
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1. 使用 DATE_FORMAT 格式化时间，更符合人类阅读习惯
            # 2. 按创建时间倒序（DESC），最新的日记排在最前面
            sql = """
                  SELECT id, \
                         visual_emotion, \
                         confidence, \
                         text_content, \
                         healing_message, \
                         DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i') as formatted_time
                  FROM diaries
                  WHERE user_id = %s
                    AND deleted_at IS NULL
                  ORDER BY created_at DESC \
                  LIMIT 100
                  """
            cursor.execute(sql,(user["id"],))
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
def _analyze_image_sync(contents: bytes) -> dict:
    image = Image.open(io.BytesIO(contents))
    image = ImageOps.exif_transpose(image)

    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=413,
            detail="图片尺寸过大",
        )

    image = image.convert("RGB")
    img_cv2 = cv2.cvtColor(
        np.array(image),
        cv2.COLOR_RGB2BGR,
    )
    h, w, _ = img_cv2.shape

    with _inference_lock:
        results = face_detector.predict(
            img_cv2,
            conf=0.2,
            device=0 if torch.cuda.is_available() else "cpu",
            verbose=False,
        )
        boxes = results[0].boxes

        if len(boxes) == 0:
            return {
                "status": "error",
                "message": "画面中没有检测到人脸",
            }

        x1, y1, x2, y2 = (
            boxes[0]
            .xyxy[0]
            .cpu()
            .numpy()
            .astype(int)
        )

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        face_img_cv2 = img_cv2[y1:y2, x1:x2]
        face_pil = Image.fromarray(
            cv2.cvtColor(face_img_cv2, cv2.COLOR_BGR2RGB)
        )

        input_tensor = (
            val_transform(face_pil)
            .unsqueeze(0)
            .to(device)
        )

        with torch.inference_mode():
            outputs = emotion_model(input_tensor)
            prob = torch.nn.functional.softmax(outputs[0], dim=0)
            score, preds = torch.max(prob, dim=0)
            emotion_idx = preds.item()
            confidence_pct = round(score.item() * 100, 1)

    final_emotion = idx_to_emotion.get(
        emotion_idx,
        "neutral",
    ).lower()
    healing_message = get_random_message(final_emotion)

    return {
        "status": "success",
        "data": {
            "emotion": final_emotion,
            "confidence": confidence_pct,
            "message": healing_message,
            "face_box": {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
            },
        },
    }
@app.post("/api/analyze")
async def analyze_emotion(file: UploadFile = File(...)):
    try:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=415,
                detail="仅支持 JPG、PNG 或 WebP 图片",
            )

        contents = await read_upload_limited(
            file,
            MAX_IMAGE_BYTES,
        )
        return await run_in_threadpool(
            _analyze_image_sync,
            contents,
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"图片分析失败: {exc}")
        raise HTTPException(
            status_code=500,
            detail="图片分析失败",
        )

# ==========================================
# 7. 新增接口：视频抽帧分析
# ==========================================
def _analyze_video_sync(temp_video_path: str) -> dict:
    if not _video_job_slot.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="当前视频分析任务繁忙，请稍后重试",
        )

    cap = None

    try:
        cap = cv2.VideoCapture(temp_video_path)

        if not cap.isOpened():
            return {
                "status": "error",
                "message": "无法打开视频文件",
            }

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_total = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        if fps and frame_total:
            duration = frame_total / fps

            if duration > MAX_VIDEO_SECONDS:
                raise HTTPException(
                    status_code=413,
                    detail="视频不能超过 60 秒",
                )

        analysis_fps = 2
        frame_skip = (
            max(1, round(fps / analysis_fps))
            if fps
            else 10
        )

        frame_count = 0
        processed_results = []

        while True:
            if (
                len(processed_results)
                >= MAX_ANALYZED_VIDEO_FRAMES
            ):
                break

            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            if frame_count % frame_skip != 0:
                continue

            h, w, _ = frame.shape

            with _inference_lock:
                results = face_detector.predict(
                    frame,
                    conf=0.2,
                    device=0 if torch.cuda.is_available() else "cpu",
                    verbose=False,
                )
                boxes = results[0].boxes

                if len(boxes) == 0:
                    continue

                x1, y1, x2, y2 = (
                    boxes[0]
                    .xyxy[0]
                    .cpu()
                    .numpy()
                    .astype(int)
                )

                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)

                face_img_cv2 = frame[y1:y2, x1:x2]
                face_pil = Image.fromarray(
                    cv2.cvtColor(
                        face_img_cv2,
                        cv2.COLOR_BGR2RGB,
                    )
                )

                input_tensor = (
                    val_transform(face_pil)
                    .unsqueeze(0)
                    .to(device)
                )

                with torch.inference_mode():
                    outputs = emotion_model(input_tensor)
                    prob = torch.nn.functional.softmax(
                        outputs[0],
                        dim=0,
                    )
                    score, preds = torch.max(prob, dim=0)
                    emotion_idx = preds.item()
                    confidence_pct = round(
                        score.item() * 100,
                        1,
                    )

            final_emotion = idx_to_emotion.get(
                emotion_idx,
                "neutral",
            ).lower()

            processed_results.append({
                "emotion": final_emotion,
                "confidence": confidence_pct,
            })

        if not processed_results:
            return {
                "status": "error",
                "message": "视频中没有检测到清晰的人脸",
            }

        emotions = [
            result["emotion"]
            for result in processed_results
        ]
        dominant_emotion = max(
            set(emotions),
            key=emotions.count,
        )
        average_confidence = sum(
            result["confidence"]
            for result in processed_results
        ) / len(processed_results)

        return {
            "status": "success",
            "data": {
                "dominant_emotion": dominant_emotion,
                "average_confidence": round(
                    average_confidence,
                    1,
                ),
                "message": get_random_message(
                    dominant_emotion
                ),
                "total_frames_analyzed": len(
                    processed_results
                ),
            },
        }
    finally:
        if cap is not None:
            cap.release()

        _video_job_slot.release()
@app.post("/api/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    temp_video_path = None

    try:
        if file.content_type not in ALLOWED_VIDEO_TYPES:
            raise HTTPException(
                status_code=415,
                detail="仅支持 MP4、MOV 或 WebM 视频",
            )

        temp_video_path = await save_video_upload_limited(
            file,
            MAX_VIDEO_BYTES,
        )
        return await run_in_threadpool(
            _analyze_video_sync,
            temp_video_path,
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"视频分析失败: {exc}")
        raise HTTPException(
            status_code=500,
            detail="视频分析失败",
        )
    finally:
        if (
            temp_video_path
            and os.path.exists(temp_video_path)
        ):
            try:
                os.remove(temp_video_path)
            except OSError:
                pass
