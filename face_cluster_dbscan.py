import numpy as np
from sklearn.cluster import DBSCAN


def face_cluster(feature_save_path,label_file_path,logger):
    # 加载特征向量（假设 float32）
    features = np.fromfile(feature_save_path, dtype=np.float32)
    features = features.reshape(-1, 512)

    # 再次归一化（确保特征是单位向量）
    features = features / np.linalg.norm(features, axis=1, keepdims=True)

    # 聚类（使用余弦距离）
    clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine').fit(features)
    labels = clustering.labels_

    # 输出聚类结果
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)

    logger.info(f"共聚类出 {n_clusters} 个簇，{n_noise} 个被识别为陌生人")

    # 保存聚类结果
    np.save(label_file_path, labels)
    logger.info(f"聚类标签已保存，数量: {len(labels)}")
