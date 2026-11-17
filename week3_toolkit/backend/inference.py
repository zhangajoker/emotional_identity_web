import cv2
import torch
from ultralytics import YOLO
from torchvision import transforms
from PIL import Image
import torch.nn as nn
from torchvision import models

# 1. 配置路径与设备
FACE_MODEL_PATH = r"D:\PyCharm\视觉实训\vision-prac\week3_toolkit\backend\model\yolo_face.pt"
EMOTION_MODEL_PATH = r"D:\PyCharm\视觉实训\vision-prac\week3_toolkit\backend\model\rafdb_emotion.pt"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 2. 加载模型
print("正在加载模型...")
face_detector = YOLO(FACE_MODEL_PATH)

# 重建 ResNet50 架构 (必须与你训练时的一致)
emotion_model = models.resnet50(weights=None)
num_ftrs = emotion_model.fc.in_features
emotion_model.fc = nn.Linear(num_ftrs, 7)

# 加载权重
checkpoint = torch.load(EMOTION_MODEL_PATH, map_location=device)
state_dict = checkpoint.get('model_state', checkpoint)
state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
emotion_model.load_state_dict(state_dict)
emotion_model.to(device)
emotion_model.eval()

EMOTION_LABELS = ['Anger', 'Disgust', 'Fear', 'Happiness', 'Neutral', 'Sadness', 'Surprise']

# 3. 预处理
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def process_image(image_path):
    """
    实现本地图片推理逻辑
    """
    # 读取图片
    img_cv2 = cv2.imread(image_path)
    if img_cv2 is None:
        print("无法读取图片！")
        return

    # YOLO 检测
    results = face_detector.predict(img_cv2, conf=0.5, verbose=False)
    boxes = results[0].boxes

    if len(boxes) == 0:
        print("未检测到人脸")
        return

    # 获取坐标
    x1, y1, x2, y2 = boxes[0].xyxy[0].cpu().numpy().astype(int)

    # 裁剪并推理
    face_img = img_cv2[y1:y2, x1:x2]
    face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))

    input_tensor = transform(face_pil).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = emotion_model(input_tensor)
        _, preds = torch.max(outputs, 1)
        emotion = EMOTION_LABELS[preds.item()]

    print(f"检测结果: {emotion}")

    # 可选：显示结果
    cv2.rectangle(img_cv2, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(img_cv2, emotion, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.imshow("Result", img_cv2)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# 测试代码
if __name__ == "__main__":
    test_img = r"D:\PyCharm\视觉实训\vision-prac\Week2_toolkit\data\week2_output\01_detection_dataset\all\images\week1_000079_P0307_f000260.jpg"# 修改为你的测试图片
    process_image(test_img)