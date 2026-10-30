import os
import shutil
from pathlib import Path

def get_user_data_dir() -> Path:
    app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    aura_dir = Path(app_data) / 'AuraAI'
    aura_dir = Path(app_data) / 'AuraAI'
    aura_dir.mkdir(parents=True, exist_ok=True)
    
    # Auto-migrate api_keys if aura doesn't have it yet
    aura_config = aura_dir / 'config'
    aura_config.mkdir(parents=True, exist_ok=True)
    aura_keys = aura_config / 'api_keys.json'
    aura_keys = aura_dir / 'config' / 'api_keys.json'
    if not aura_keys.exists() and aura_keys.exists():
        try:
            shutil.copy2(aura_keys, aura_keys)
        except Exception:
            pass
            
    return aura_dir
