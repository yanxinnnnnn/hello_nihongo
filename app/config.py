import yaml
import logging

class Config:
    def __init__(self, config_file: str = 'config.yaml'):
        self.config_file = config_file
        self.config_data = self.load_config()
        self.setup_logging()
        
    def load_config(self) -> dict:
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except FileNotFoundError:
            logging.error(f'配置文件{self.config_file}未找到，使用默认配置。')
            return {}
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config_data
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, ValueError):
            return default
    
    def setup_logging(self):
        log_level = self.get('logging.level', 'INFO').upper()
        log_format = self.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = self.get('logging.file', 'app.log')
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
config = Config()