import os
import cv2
import numpy as np
import base64
from collections import defaultdict

def generate_report(HTML_REPORT_PATH,LABELS_PATH,FACE_PATHS_TXT):

    with open(FACE_PATHS_TXT, 'r') as f:
        face_paths = [line.strip() for line in f]

    labels = np.load(LABELS_PATH)

    cluster_dict = defaultdict(list)
    for path, label in zip(face_paths, labels):
        cluster_dict[label].append(path)

    html = []
    html.append("<html><head><meta charset='utf-8'><title>人脸聚类报告</title>")
    html.append("<style>")
    html.append("body { font-family: Arial, sans-serif; }")
    html.append(".cluster { margin-bottom: 40px; }")
    html.append(".cluster-title { font-size: 20px; margin-bottom: 10px; }")
    html.append(".thumb { margin: 5px; border: 1px solid #ccc; display: inline-block; }")
    html.append(".thumb img { display: block; width: 112px; height: 112px; object-fit: cover; }")
    html.append(".thumb-caption { font-size: 10px; text-align: center; width: 112px; word-break: break-word; }")
    html.append("</style></head><body>")
    html.append("<h1>人脸聚类报告</h1>")
    html.append(f"<p>共聚类出 {len(cluster_dict) - (1 if -1 in cluster_dict else 0)} 个簇，陌生人（噪声点）数量：{len(cluster_dict.get(-1, []))}</p>")

    for label, paths in sorted(cluster_dict.items()):
        label_name = "陌生人 (-1)" if label == -1 else f"聚类 {label}"
        html.append(f"<div class='cluster'>")
        html.append(f"<div class='cluster-title'>{label_name} - 共 {len(paths)} 张图片</div>")
        for p in paths:
            img_path = p.split('#')[0]
            # 直接用绝对路径作为img src
            if os.path.exists(img_path):
                html.append("<div class='thumb'>")
                html.append(
                    f"<img src='file:///{img_path}' alt='{os.path.basename(p)}' style='width:112px;height:112px;object-fit:cover;'/>")
                html.append(f"<div class='thumb-caption'>{os.path.basename(p)}</div>")
                html.append("</div>")
        html.append("</div>")

    html.append("</body></html>")

    with open(HTML_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html))

    print(f"聚类报告已生成：{HTML_REPORT_PATH}")
