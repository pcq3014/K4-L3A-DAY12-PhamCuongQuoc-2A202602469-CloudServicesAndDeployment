"""CP3 — Rate limiting bằng thuật toán sliding window.

Đếm số request trong 60 giây **gần nhất** (cửa sổ trượt), thay vì đếm theo
phút đồng hồ. Đếm theo phút đồng hồ có lỗ hổng: 10 request lúc 10:00:59 và
10 request lúc 10:01:01 = 20 request trong 2 giây mà vẫn "đúng luật".

Cấu trúc dữ liệu: Redis Sorted Set (ZSET), score = timestamp của request.
"""

from __future__ import annotations

import time
import uuid

from fastapi import HTTPException, status

WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, client, limit_per_minute: int) -> None:
        self.client = client
        self.limit = limit_per_minute

    @staticmethod
    def _key(user_id: str) -> str:
        """CHO SẴN — mỗi user một key riêng."""
        return f"ratelimit:{user_id}"

    def hit_count(self, user_id: str, now: float | None = None) -> int:
        """Số request của user trong ``WINDOW_SECONDS`` giây gần nhất.

        TODO (CP3):
          1. ``now = now if now is not None else time.time()``
          2. Xóa các entry cũ hơn cửa sổ:
             ``self.client.zremrangebyscore(key, 0, now - WINDOW_SECONDS)``
          3. Trả về ``self.client.zcard(key)``
        """
        now = now if now is not None else time.time()
        key = self._key(user_id)
        self.client.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        return int(self.client.zcard(key))

    def check(self, user_id: str, now: float | None = None) -> None:
        """Cho qua nếu còn quota, ngược lại raise 429.

        TODO (CP3):
          1. ``now = now if now is not None else time.time()``
          2. Gọi ``self.hit_count(user_id, now)``.
          3. Nếu số đó ``>= self.limit`` → raise
             ``HTTPException(status_code=429, detail="rate limit exceeded",
                             headers={"Retry-After": str(WINDOW_SECONDS)})``
          4. Chưa vượt → ghi nhận request này:
             ``self.client.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})``
             (member phải là chuỗi DUY NHẤT, nếu không hai request cùng
             timestamp sẽ ghi đè nhau và bạn đếm thiếu)
             rồi ``self.client.expire(key, WINDOW_SECONDS)`` để key tự dọn.

        Lưu ý thứ tự: **kiểm tra trước, ghi nhận sau**. Ghi trước rồi mới đếm
        sẽ chặn nhầm ngay ở request thứ ``limit``.
        """
        now = now if now is not None else time.time()
        key = self._key(user_id)
        member = f"{now}:{uuid.uuid4().hex}"

        # Dọn + ghi + đếm trong MỘT transaction (MULTI/EXEC). Nếu tách thành
        # "đếm rồi mới ghi", hai instance cùng lúc có thể cùng thấy còn quota
        # và cùng cho qua → vượt hạn mức khi scale ngang.
        pipe = self.client.pipeline(transaction=True)
        pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SECONDS)
        _, _, count, _ = pipe.execute()

        if count > self.limit:
            # Request bị chặn không được tính vào quota
            self.client.zrem(key, member)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(self._retry_after(key, now))},
            )

    def _retry_after(self, key: str, now: float) -> int:
        """Số giây tới khi request cũ nhất rời khỏi cửa sổ (tối thiểu 1)."""
        oldest = self.client.zrange(key, 0, 0, withscores=True)
        if not oldest:
            return WINDOW_SECONDS
        return max(1, int(oldest[0][1] + WINDOW_SECONDS - now) + 1)
