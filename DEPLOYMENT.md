# Thông Tin Deploy — Checkpoint 5

> Điền file này sau khi deploy xong. `pytest tests/test_cp5.py` đọc file này
> để tìm địa chỉ service của bạn và gọi thử.
>
> **Chỉ ghi TÊN biến môi trường, tuyệt đối không dán giá trị API key vào đây.**
> Repo này công khai — dán khóa vào là mất khóa.

## Thông Tin Học Viên

| Mục | Nội dung |
|-----|----------|
| Họ và tên | Phạm Cường Quốc |
| Mã học viên | 2A202602469 |
| Repo | https://github.com/pcq3014/K4-L3A-DAY12-PhamCuongQuoc-2A202602469-CloudServicesAndDeployment |

## Service

| Mục | Nội dung |
|-----|----------|
| Public URL | https://k4-l3a-day12-phamcuongquoc-2a202602469.onrender.com |
| Platform | Render — Web Service (Docker, free) + Render Key Value (Redis, free) |
| Ngày deploy | 2026-09-28 |

## Biến Môi Trường Đã Set Trên Cloud

Ghi tên biến và **nguồn giá trị**, không ghi giá trị:

| Biến | Đã set | Ghi chú |
|------|--------|---------|
| `PORT` | ✅ | Render tự gán, Dockerfile đọc qua `${PORT}` |
| `AGENT_API_KEY` | ✅ | đặt trong tab Environment của Render, không nằm trong repo |
| `REDIS_URL` | ✅ | Internal URL của instance Render Key Value (cùng region, chỉ mạng nội bộ) |
| `RATE_LIMIT_PER_MINUTE` | ✅ | 10 — dùng giá trị mặc định trong `Settings` nếu không set |
| `MONTHLY_BUDGET_USD` | ✅ | 10.0 — dùng giá trị mặc định trong `Settings` nếu không set |
| `LOG_LEVEL` | ✅ | INFO — dùng giá trị mặc định trong `Settings` nếu không set |

## Lệnh Kiểm Tra

Thay `<URL>` bằng Public URL ở trên:

```bash
# 1. Liveness — mong đợi 200 {"status":"ok"}
curl -i <URL>/health

# 2. Readiness — mong đợi 200 {"status":"ready"} (đã nối được Redis)
curl -i <URL>/ready

# 3. Không có API key — mong đợi 401
curl -i -X POST <URL>/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

# 4. Có API key — mong đợi 200 kèm câu trả lời
curl -i -X POST <URL>/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "X-User-Id: sv-test" \
  -d '{"question":"Deploy là gì?"}'

# 5. Rate limit — gọi 15 lần, những lần cuối phải trả 429
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST <URL>/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "X-User-Id: sv-test" \
    -d '{"question":"test"}'
done; echo
```

## Kết Quả Chạy Thật

Dán output của các lệnh trên vào đây:

Chạy ngày 2026-09-28 vào Public URL ở trên (chỉ giữ dòng status và body):

```
$ curl -i <URL>/health
HTTP/1.1 200 OK
{"status":"ok","service":"day12-agent","version":"1.0.0"}

$ curl -i <URL>/ready
HTTP/1.1 200 OK
{"status":"ready","redis":true}

$ curl -i -X POST <URL>/ask            # không có API key
HTTP/1.1 401 Unauthorized
{"detail":"invalid or missing API key"}

$ curl -i -X POST <URL>/ask            # có API key, X-User-Id: sv-test — gọi 2 lần
HTTP/1.1 200 OK
{"answer":"Câu hỏi hay. Deploy là gì thường được giải quyết bằng cách chuẩn hóa môi trường chạy: cùng một image chạy giống nhau ở laptop và trên cloud.","user_id":"sv-test","history_length":0,"cost_usd":2.145e-05,"tokens":{"in":3,"out":35}}
HTTP/1.1 200 OK
{"answer":"Câu hỏi hay. Deploy là gì thường được giải quyết bằng cách chuẩn hóa môi trường chạy: cùng một image chạy giống nhau ở laptop và trên cloud. (Mình đang nhớ 2 lượt trao đổi trước đó.)","user_id":"sv-test","history_length":2,"cost_usd":3.315e-05,"tokens":{"in":41,"out":45}}

$ # Rate limit — 15 request liên tiếp (X-User-Id: rl-test)
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

Ghi chú khi chạy trên Windows: gửi câu hỏi có dấu tiếng Việt thẳng trong
tham số `-d` của curl (Git Bash) bị lỗi mã hóa → server trả 400
"error parsing the body". Ghi body ra file UTF-8 rồi gửi bằng
`--data-binary @body.json` thì trả 200 như trên.

## Ảnh Chụp Màn Hình

Đặt ảnh trong thư mục `screenshots/`:

- `screenshots/dashboard.png` — trang quản lý service trên platform
- `screenshots/health.png` — kết quả gọi `/health` từ trình duyệt hoặc curl
