from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_host: str
    llm_key: str
    llm_model: str = "oss-120b"

    protocols_path: str = "./corpus/protocols_corpus.jsonl"
    top_k: int = 3
    chunk_limit: int = 700
    icd_limit: int = 10

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()