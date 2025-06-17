
import os
import time

import face_cluster_dbscan
import utils
import visualize_clusters_by_dbscan
# 从face-features.py导入需要的函数
from face_features import process_images_incrementally
# 从ftp-download.py导入需要的函数
from ftp_download import download_new_images_from_ftp


# 初始化日志
logger = utils.setup_logger('main')

if __name__ == '__main__':
    processed_set = set()
    if os.path.exists(process_file_path):
        with open(process_file_path) as f:
            processed_set = set(line.strip() for line in f)

    while True:
        # 1. 下载新图像
        download_new_images_from_ftp(
            ftp_host=FTP_HOST,
            ftp_user=FTP_USER,
            ftp_pass=FTP_PASS,
            remote_dir=REMOTE_DIR,
            local_dir=img_dir,
            processed_files=processed_set,logger=logger,
        )

        # 2. 增量处理
        process_images_incrementally(
            path_list_file= path_list_file,
            image_dir=img_dir,
            feature_save_path= feature_save_path,
            processed_files_set=processed_set,logger=logger,
        )

        # 3.处理聚类
        face_cluster_dbscan.face_cluster(feature_save_path=feature_save_path, label_file_path=label_file_path,logger=logger)
        # 3. 保存处理状态
        with open(process_file_path, 'w') as f:
            for fname in processed_set:
                f.write(fname + '\n')
        #5.生成报告
        visualize_clusters_by_dbscan.generate_report(HTML_REPORT_PATH,label_file_path,path_list_file)

        time.sleep(10)  # 每10秒轮询一次
