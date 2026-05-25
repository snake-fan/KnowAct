from backend.knowact.llm.config import load_dotenv_file


load_dotenv_file()

from backend.knowact.logging_config import configure_knowact_logging


configure_knowact_logging()

from backend.knowact.api.app import create_app


app = create_app()
