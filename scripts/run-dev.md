# Development Run Instructions

## Terminal 1: Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
# Copy .env.example to .env and add keys
uvicorn app.main:app --reload --port 8000
```

## Terminal 2: Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000
