# Cluster Faces by dbscan

## Intorduction
采用了无监督方法dbscan进行人脸聚类，可适用于安防场景，识别出陌生人；本项目仅为算法部分实现。
该项目包含完整流程，从FTP获取人脸照片->使用insightface提取特征点->通过dbscan进行人脸聚类->生成聚类报告html供验证
目前支持定时增量汇聚分析；


## Requirements
* tqdm
* numpy==1.26.4
* scipy
* scikit-learn
* torch==2.3.1
* torchvision==0.18.1
* torchaudio==2.3.1
* faiss-cpu==1.8.0 (or faiss-gpu)
* onnxruntime-gpu
* insightface 采用whl安装

## Run
* 修改config.ini的配置
* 执行main.py
```bash
python main.py
```
## ShowReport
```bash
  ./files/cluster_report.html
```

