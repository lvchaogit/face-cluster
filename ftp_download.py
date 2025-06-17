import ftplib
import os
import time
from ftplib import FTP
from socket import timeout

import utils


# 初始化日志
def download_new_images_from_ftp(ftp_host, ftp_user, ftp_pass, remote_dir, local_dir, processed_files, logger,max_retries=3,retry_delay=10, timeout_sec=60):
    """
    从FTP下载新图片文件（带重试和断点续传）

    参数:
    ftp_host -- FTP主机地址
    ftp_user -- FTP用户名
    ftp_pass -- FTP密码
    remote_dir -- 远程目录
    local_dir -- 本地保存目录
    processed_files -- 已处理文件集合
    max_retries -- 最大重试次数 (默认3)
    retry_delay -- 重试延迟(秒) (默认10)
    timeout_sec -- 超时时间(秒) (默认60)

    返回: 成功下载的文件列表
    """
    downloaded_files = []
    ftp = None

    try:
        # 创建FTP连接
        ftp = FTP(ftp_host, timeout=timeout_sec)
        ftp.login(ftp_user, ftp_pass)
        ftp.set_pasv(True)  # 启用被动模式
        ftp.cwd(remote_dir)
        logger.info('成功连接到FTP服务器: %s', ftp_host)

        # 获取文件列表
        filenames = ftp.nlst()
        new_files = [f for f in filenames if '_FACE_SNAP' in f and f not in processed_files]
        logger.info('发现 %d 个新文件需要下载', len(new_files))

        if not new_files:
            return []

        # 确保本地目录存在
        os.makedirs(local_dir, exist_ok=True)

        # 下载每个文件
        for fname in new_files:
            local_path = os.path.join(local_dir, fname)
            success = download_file_with_retry(
                ftp, fname, local_path,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout_sec=timeout_sec
            )

            if success:
                downloaded_files.append(fname)
                processed_files.add(fname)
                logger.info('成功下载: %s', fname)
            else:
                logger.error('下载失败: %s', fname)

    except Exception as e:
        logger.error('FTP操作失败: %s', str(e), exc_info=True)
    finally:
        # 确保关闭FTP连接
        if ftp:
            try:
                ftp.quit()
            except:
                try:
                    ftp.close()
                except:
                    pass
            logger.info('已断开FTP连接')

    logger.info('下载完成: %d/%d 个文件成功下载', len(downloaded_files), len(new_files))
    return downloaded_files


def download_file_with_retry(ftp, remote_file, local_path, max_retries=3, retry_delay=10, timeout_sec=60):
    """
    带重试机制的单个文件下载（支持断点续传）

    参数:
    ftp -- FTP连接对象
    remote_file -- 远程文件名
    local_path -- 本地文件路径
    max_retries -- 最大重试次数
    retry_delay -- 重试延迟(秒)
    timeout_sec -- 超时时间(秒)

    返回: 是否下载成功
    """
    attempts = 0
    start_pos = 0

    # 检查文件是否已存在（部分下载）
    if os.path.exists(local_path):
        local_size = os.path.getsize(local_path)
        try:
            # 获取远程文件大小
            ftp.sendcmd("TYPE I")  # 切换到二进制模式
            remote_size = ftp.size(remote_file)

            # 如果本地文件较小，尝试续传
            if 0 < local_size < remote_size:
                logger.info('尝试续传: %s (已下载 %d/%d 字节)', remote_file, local_size, remote_size)
                start_pos = local_size
            else:
                # 文件已完整下载或无效
                os.remove(local_path)
                logger.info('删除无效文件: %s', local_path)
        except:
            # 无法获取远程大小，删除本地文件
            os.remove(local_path)
            logger.warning('无法获取远程文件大小，删除本地文件: %s', local_path)

    # 重试循环
    while attempts < max_retries:
        attempts += 1
        try:
            # 设置套接字超时
            ftp.sock.settimeout(timeout_sec)

            # 下载文件（续传或新下载）
            mode = 'ab' if start_pos > 0 else 'wb'
            with open(local_path, mode) as f:
                # 回调函数
                def callback(data):
                    f.write(data)

                # 执行下载
                ftp.retrbinary(
                    'RETR ' + remote_file,
                    callback,
                    rest=start_pos,
                    blocksize=32768  # 32KB块大小
                )

            # 验证下载
            final_size = os.path.getsize(local_path)
            try:
                remote_size = ftp.size(remote_file)
                if remote_size is not None and final_size != remote_size:
                    raise IOError(f"文件大小不匹配: 本地 {final_size} != 远程 {remote_size}")
            except:
                pass  # 无法验证大小

            return True

        except (timeout, TimeoutError, ftplib.error_temp, ftplib.all_errors) as e:
            # 处理超时和临时错误
            logger.warning('下载错误 (尝试 %d/%d): %s - %s', attempts, max_retries, remote_file, str(e))

            # 获取当前下载位置
            current_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            start_pos = current_size

            if attempts < max_retries:
                logger.info('等待 %d 秒后重试...', retry_delay)
                time.sleep(retry_delay)

                # 尝试重新连接
                try:
                    ftp = reconnect_ftp(ftp)
                except Exception as e:
                    logger.error('重新连接失败: %s', str(e))

        except Exception as e:
            # 处理其他错误
            logger.error('下载失败: %s - %s', remote_file, str(e), exc_info=True)
            break

    # 下载失败处理
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
            logger.info('已删除不完整文件: %s', local_path)
        except:
            pass

    return False


def reconnect_ftp(ftp):
    """重新建立FTP连接"""
    try:
        # 获取原始连接参数
        host = ftp.host
        user = ftp.user
        passwd = ftp.passwd
        timeout = ftp.timeout

        # 关闭旧连接
        try:
            ftp.quit()
        except:
            try:
                ftp.close()
            except:
                pass

        # 创建新连接
        new_ftp = FTP(host, timeout=timeout)
        new_ftp.login(user, passwd)
        new_ftp.set_pasv(True)

        # 恢复原始工作目录
        try:
            if hasattr(ftp, 'pwd'):
                new_ftp.cwd(ftp.pwd())
        except:
            pass

        logger.info('FTP连接已重新建立')
        return new_ftp
    except Exception as e:
        logger.error('FTP重新连接失败: %s', str(e))
        raise


# 使用示例
if __name__ == "__main__":
    # 配置参数
    FTP_HOST = 'ftp.example.com'
    FTP_USER = 'your_username'
    FTP_PASS = 'your_password'
    REMOTE_DIR = '/photos'
    LOCAL_DIR = './downloaded'

    # 初始化已处理文件集合
    processed_files = set()

    # 运行下载
    try:
        downloaded = download_new_images_from_ftp(
            FTP_HOST, FTP_USER, FTP_PASS,
            REMOTE_DIR, LOCAL_DIR, processed_files,
            max_retries=3,
            retry_delay=15,
            timeout_sec=90
        )
        print(f"成功下载的文件: {downloaded}")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
