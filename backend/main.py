from backend.knowact.llm.config import load_dotenv_file


load_dotenv_file()

from backend.knowact.api.app import create_app


app = create_app()
