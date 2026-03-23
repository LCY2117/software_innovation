运行指令

```bash
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

**方式 B：后台静默运行 (正式用，永不掉线) —— ⭐ 推荐**

```bash
nohup uvicorn server:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &

```