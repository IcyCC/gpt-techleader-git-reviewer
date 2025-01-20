import logging
from datetime import datetime
from typing import List, Optional, Tuple

from app.infra.config.settings import get_settings

from .comment import Comment, CommentPosition, CommentType
from .git import FileDiff, MergeRequest
from .review import ReviewResult

logger = logging.getLogger(__name__)


class SizeChecker:
    """检查 MR 和文件大小的类"""

    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.settings = get_settings()

    def check_mr_size(self, mr: MergeRequest) -> Optional[ReviewResult]:
        """检查 MR 大小，如果太大返回 ReviewResult"""
        if len(mr.file_diffs) > self.settings.MAX_FILES_PER_MR:
            logger.warning(
                f"MR 文件数量过多: {len(mr.file_diffs)} > {self.settings.MAX_FILES_PER_MR}"
            )
            return ReviewResult(
                mr_id=mr.mr_id,
                summary=f"⚠️ 此 MR 包含 {len(mr.file_diffs)} 个文件，超过了最大限制 {self.settings.MAX_FILES_PER_MR} 个。\n建议将大型 MR 拆分为多个小型 MR，以便更好地进行代码审查。",
                overall_status="commented",
                review_date=datetime.utcnow(),
            )
        return None

    def check_files_size(
        self, mr: MergeRequest
    ) -> Tuple[List[FileDiff], List[FileDiff]]:
        """检查文件大小，回大文件评论、大文件列表、正常文件列表和总结"""
        large_files = []
        normal_files = []

        for file_diff in mr.file_diffs:
            if file_diff.diff_content:
                lines = file_diff.diff_content.count("\n") + 1
                if lines > self.settings.MAX_LINES_PER_FILE or len(file_diff.diff_content) > self.settings.MAX_BYTES_PER_FILE:
                    large_files.append(file_diff)
                else:
                    normal_files.append(file_diff)

        return large_files, normal_files

    def create_large_file_comment(
        self, mr: MergeRequest, file_diff: FileDiff, lines: int
    ) -> Comment:
        """创建大文件评论"""
        return Comment(
            comment_id=f"large_file_{datetime.utcnow().timestamp()}",
            author=self.bot_name,
            content=f"⚠️ 此文件有 {lines} 行代码，超过了建议的最大行数 {self.settings.MAX_LINES_PER_FILE} 行。\n建议将大文件拆分为多个小文件，以提高代码的可维护性。",
            created_at=datetime.utcnow(),
            comment_type=CommentType.FILE,
            mr_id=mr.mr_id,
            position=CommentPosition(new_file_path=file_diff.new_file_path, old_file_path=file_diff.old_file_path, new_line_number=1),
        )

    def create_large_files_summary(self, large_files: List[FileDiff]) -> str:
        """创建大文件总结"""
        summary = (
            f"以下文件超过了最大行数限制 ({self.settings.MAX_LINES_PER_FILE} 行)：\n"
        )
        for file_diff in large_files:
            summary += f"- {file_diff.new_file_path}: {len(file_diff.diff_content)} 行\n"
        summary += "\n建议将大文件拆分为多个小文件，以提高代码的可维护性。"
        return summary
