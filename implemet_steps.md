I'll provide a clear, step-by-step guide to help you start the project. Let me create a simplified getting started guide.

## 🚀 **Simple Step-by-Step Guide to Start the Project**

Let me break this down into the simplest possible steps:

### **Step 1: Check Prerequisites**
```bash
# Make sure you have Redis and MySQL running
redis-cli ping
# Should return: PONG

mysql -u root -p -e "SHOW DATABASES;"
# Should show crawler_db and arxiv_db
```

### **Step 2: Activate Virtual Environment**
```bash
cd /Users/charan/Downloads/MU/sem4/distributed-web-crawler-github/Distriubuted-Web-Crawler
source venv/bin/activate
```

### **Step 3: Start the System (3 Commands)**
```bash
# Command 1: Start Celery workers
python worker.py --worker-id worker-1 &
python worker.py --worker-id worker-2 &

# Command 2: Add URLs to crawl
python seed.py --default

# Command 3: Start crawling
python main.py --seeds "https://example.com" --no-monitor
```

### **Step 4: Check if it's Working**
```bash
# Check queue status
python seed.py --status

# Check what workers are doing
celery -A celery_app inspect active
```

### **Step 5: Stop the System**
```bash
# Stop all workers
pkill -f "celery worker"
pkill -f "python worker.py"
```

---

## **🔍 If Something Goes Wrong**

### **Problem: Redis not running**
```bash
# Start Redis
redis-server
```

### **Problem: Workers not starting**
```bash
# Check Celery configuration
python -c "from celery_app import app; print('Celery OK')"

# Start worker with debug info
python worker.py --worker-id debug-worker --loglevel debug
```

### **Problem: No tasks processing**
```bash
# Clear queues and restart
redis-cli flushall
python seed.py --default
```

---

## **📋 Quick Test (Just to verify it works)**

```bash
# Test with a simple URL
python main.py --seeds "https://httpbin.org/html" --no-monitor
```

You should see output showing the crawler processing the URL. If you see this, the system is working!

---

## **🎯 What Each Command Does**

1. **`python worker.py`**: Starts crawler workers that actually process URLs
2. **`python seed.py --default`**: Adds some test URLs to the queue  
3. **`python main.py --seeds`**: Tells the workers to start crawling

The **`&`** at the end runs commands in the background so you can run multiple workers at once.

---

**Try these steps and let me know if you get stuck at any specific step!**