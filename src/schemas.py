from pydantic import BaseModel, Field

class DiagnoseIn(BaseModel):
    symptoms: str

class Diagnosis(BaseModel):
    rank: int
    diagnosis: str
    icd10_code: str = Field(..., alias="icd10_code")
    explanation: str

class DiagnoseOut(BaseModel):
    diagnoses: list[Diagnosis] = []