import os

import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from torch.utils.data import Dataset, DataLoader


# 创建数据集类定义
class FaceDataset(Dataset):
    def __init__(self, image_dir):
        self.image_dir = image_dir
        self.image_paths = []

        # 获取所有图片路径
        for root, _, files in os.walk(image_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')) and '_FACE_SNAP' in file:
                    self.image_paths.append(os.path.join(root, file))

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        # 使用OpenCV读取图像，因为InsightFace使用BGR格式
        image = cv2.imread(img_path)
        if image is None:
            # 如果图像无法读取，返回一个空数组和路径
            return np.zeros((3, 112, 112)), img_path
        return image, img_path


# 主函数，包含所有处理逻辑
def custom_collate_fn(batch):
    # 分离图像和路径
    images = [item[0] for item in batch]
    paths = [item[1] for item in batch]
    # 不将图像堆叠成张量，而是保持为列表
    return images, paths


def process_images_incrementally(image_dir, feature_save_path, processed_files_set, path_list_file,config,logger):
    # 获取FaceAnalysis配置
    model_name = config['FaceAnalysis']['model_name']
    batch_size = int(config['FaceAnalysis']['batch_size'])
    model_root = config['FaceAnalysis']['model_root']
    num_workers = int(config['FaceAnalysis']['num_workers'])

    """  增量特征提取，并合并到主特征  """
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")
    # 使用检测和识别模型，如果有GPU则使用GPU
    ctx_id = 0 if torch.cuda.is_available() else -1
    app = FaceAnalysis(name=model_name, root=model_root)
    app.prepare(ctx_id=ctx_id, det_size=(640, 640))

    new_dataset = FaceDataset(image_dir)
    # 创建数据加载器
    dataloader = DataLoader(new_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers,
                            pin_memory=True, collate_fn=custom_collate_fn)

    new_features = []
    new_paths = []

    for images, img_paths in dataloader:
        for image, img_path in zip(images, img_paths):
            try:
                fname = os.path.basename(img_path)
                if fname in processed_files_set:
                    continue

                # 确保image是numpy数组
                if isinstance(image, torch.Tensor):
                    image = image.numpy()
                # 检测人脸
                faces = app.get(image)
                if len(faces) == 0:
                    logger.info(f"未在 {img_path} 中检测到人脸")
                    processed_files_set.add(fname)
                    continue
                # 对每个检测到的人脸提取特征
                for j, face in enumerate(faces):
                    # 获取人脸特征向量
                    face_embedding = face.embedding
                    if face_embedding is not None:
                        # 存储特征和路径（对于多个人脸，我们在路径后添加索引）
                        new_features.append(face_embedding)
                        if len(faces) > 1:
                            # 如果一张图片有多个人脸，为路径添加后缀
                            face_path = f"{img_path}#face{j}"
                        else:
                            face_path = img_path
                        new_paths.append(face_path)
                        processed_files_set.add(fname)

            except Exception as e:
                logger.error(f"处理 {img_path} 时出错: {e}")

    if new_features:
        features_array = np.array(new_features, dtype=np.float32)
        features_array = features_array / np.linalg.norm(features_array, axis=1, keepdims=True)
        mode = 'wb'
        if os.path.exists(feature_save_path):
            mode = 'ab'
        os.makedirs(os.path.dirname(feature_save_path), exist_ok=True)
        with open(feature_save_path, mode) as f:
            f.write(features_array.tobytes())
        logger.info(f"标签已保存到 {feature_save_path}")

        mode = 'w'
        if os.path.exists(path_list_file):
            mode = 'a'
        with open(path_list_file, mode) as f:
            for path in new_paths:
                f.write(path + '\n')
        logger.info(f"图片路径已保存到 {path_list_file}")
