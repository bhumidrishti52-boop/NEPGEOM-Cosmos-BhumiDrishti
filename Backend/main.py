from fastapi import FASTAPI, HTTPException

app=FASTAPI()

@app.get("/")
