from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import ee
from fastapi.staticfiles import StaticFiles

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    ee.Initialize(project='flood-482116')
    print("Earth Engine Initialized Successfully")
except Exception as e:
    print(f"Auth Error: {e}")

class ChatRequest(BaseModel):
    question: str
    land_data: dict


class ReportRequest(BaseModel):
    analysis_data: dict
