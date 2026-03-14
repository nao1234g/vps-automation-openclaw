"""
board/ — ボードミーティングパッケージ

毎朝 06:00 JST に自動実行される「経営ボード会議」。
全エンジンの出力を統合し、今日最もROIの高いアクションを決定する。
"""

from board.board_meeting import BoardMeeting

__all__ = ["BoardMeeting"]
