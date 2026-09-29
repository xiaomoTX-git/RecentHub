"""
RecentHub 单例常驻后台搜索线程模块
- 解决 QThread 频繁创建与析构造成的 native 内存撕裂和闪退崩溃 (0xC0000005)
- 单线程生命周期安全持有 COM / ADODB 上下文
- 基于 Token 版本号的任务队列：自动作废过时搜索，仅计算最新输入
"""

import logging
import queue
from typing import List
from PySide6.QtCore import QThread, Signal
from app.core.models import RecentItem
from app.services.file_search_service import FileSearchService

logger = logging.getLogger(__name__)


class PersistentSearchWorker(QThread):
    results_ready = Signal(str, list)

    def __init__(self):
        super().__init__()
        self._queue = queue.Queue()
        self._current_token = 0
        self._is_running = True

    def submit_search(self, query: str):
        """主线程提交搜索请求 (非阻塞，瞬间返回)"""
        self._current_token += 1
        # 清空积压的陈旧搜索，避免无效算力消耗
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        
        q_str = query.strip()
        if q_str and len(q_str) >= 2:
            self._queue.put((self._current_token, q_str))

    def cancel_pending(self):
        """取消并清空所有未完成的任务，让线程瞬间进入休眠状态"""
        self._current_token += 1
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def ensure_started(self):
        """(重新)启动常驻线程。stop() 之后可复用同一实例：
        信号连接全部保留，无需重新 connect，避免唤出后异步全盘检索失效。"""
        self._is_running = True
        if not self.isRunning():
            self.start()

    def stop(self):
        """安全停止常驻线程：必须确认线程已真正退出再返回。
        否则 QThread 对象会在线程仍在运行时被析构，Qt 将 qFatal
        (QThread: Destroyed while thread is still running) 并以 __fastfail
        (0xC0000409) 硬崩整个进程。"""
        self._is_running = False
        try:
            self._queue.put((-1, ""))
        except Exception:
            pass
        # run() 已改为 0.2s 超时轮询，正常最迟 0.2s 内退出，这里留足裕量
        if not self.wait(3000):
            # 极端情况 (仍阻塞在外部 es.exe / COM 查询中)：强制终止，
            # 绝不允许带着存活线程析构，宁可丢弃这次无用的后台检索
            self.terminate()
            self.wait(1000)

    def run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            logger.debug("后台检索线程 CoInitialize 失败", exc_info=True)

        try:
            while self._is_running:
                try:
                    # 超时轮询而非无限阻塞：既保持近乎 0% CPU，
                    # 又保证 stop() 能在 0.2s 内让线程察觉退出请求
                    token, query = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                except Exception:
                    logger.debug("后台检索任务出队异常，退出线程循环", exc_info=True)
                    break

                if not self._is_running or token == -1:
                    break

                # 快速检查是否有更新的任务已经提交
                if token != self._current_token:
                    continue

                try:
                    items = FileSearchService.search_live(query)
                    # 再次确认仍为最新词且未被终止
                    if self._is_running and token == self._current_token:
                        self.results_ready.emit(query, items)
                except Exception:
                    logger.warning("全盘实时检索执行失败: %s", query, exc_info=True)
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
