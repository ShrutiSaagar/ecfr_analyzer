from pydantic_settings import BaseSettings

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    ECFR_BASE_URL: str = "https://www.ecfr.gov/api"
    
    class Config:
        env_file = ".env"

settings = Settings()
# os.environ.get('COSMOS_MONGO_USER')