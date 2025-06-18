
import os
import time
import configparser

import face_cluster_dbscan
import utils
import visualize_clusters_by_dbscan
# 从face-features.py导入需要的函数
from face_features import process_images_incrementally
# 从ftp-download.py导入需要的函数
from ftp_download import download_new_images_from_ftp

# 读取配置文件
def load_config(config_path='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")
    config.read(config_path, encoding='utf-8')
    return config

# 初始化日志
def init_app():
    config = load_config()
    
    # 设置日志文件路径
    utils.LOG_FILE = config['Paths']['log_file']
    logger = utils.setup_logger('main')
    logger.info("应用启动，已加载配置文件")
    
    return config, logger

if __name__ == '__main__':
    # 加载配置并初始化日志
    config, logger = init_app()
    
    # 获取路径配置
    img_dir = config['Paths']['image_dir']
    feature_save_path = config['Paths']['feature_save_path']
    path_list_file = config['Paths']['path_list_file']
    label_file_path = config['Paths']['label_file_path']
    process_file_path = config['Paths']['process_file_path']
    html_report_path = config['Paths']['html_report_path']
    
    # 获取FTP配置
    ftp_host = config['FTP']['host']
    ftp_port = int(config['FTP']['port'])
    ftp_user = config['FTP']['user']
    ftp_pass = config['FTP']['password']
    remote_dir = config['FTP']['remote_dir']
    timeout_sec = int(config['FTP']['timeout_sec'])
    max_retries = int(config['FTP']['max_retries'])
    retry_delay = int(config['FTP']['retry_delay'])


    # 获取系统配置
    poll_interval = int(config['System']['poll_interval'])
    
    # 获取聚类参数
    eps = float(config['Clustering']['eps'])
    min_samples = int(config['Clustering']['min_samples'])
    metric = config['Clustering']['metric']
    
    processed_set = set()
    if os.path.exists(process_file_path):
        with open(process_file_path) as f:
            processed_set = set(line.strip() for line in f)

    while True:
        # 1. 下载新图像
        download_new_images_from_ftp(
            ftp_host=ftp_host,
            ftp_user=ftp_user,
            ftp_pass=ftp_pass,
            remote_dir=remote_dir,
            local_dir=img_dir,
            processed_files=processed_set,
            logger=logger,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout_sec=timeout_sec
        )

        # 2. 增量处理
        process_images_incrementally(
            path_list_file=path_list_file,
            image_dir=img_dir,
            feature_save_path=feature_save_path,
            processed_files_set=processed_set,config=config,
            logger=logger
        )

        # 3.处理聚类
        face_cluster_dbscan.face_cluster(
            feature_save_path=feature_save_path, 
            label_file_path=label_file_path,
            logger=logger
        )
        
        # 4. 保存处理状态
        with open(process_file_path, 'w') as f:
            for fname in processed_set:
                f.write(fname + '\n')
                
        # 5.生成报告
        visualize_clusters_by_dbscan.generate_report(
            html_report_path,
            label_file_path,
            path_list_file
        )

        logger.info(f"完成一次处理循环，等待 {poll_interval} 秒后继续...")
        time.sleep(poll_interval)  # 使用配置的轮询间隔
