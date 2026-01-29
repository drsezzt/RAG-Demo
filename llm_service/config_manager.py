import os
import sys
import json
from logging import getLogger

MODELS_CONFIG_PATH = os.path.dirname(os.path.abspath(__file__)) + "/config/models_path.json"
logger = getLogger("LLM")

def load_model_configs():
    logger.info(
        "op=model_config_load_start"
        f"path={MODELS_CONFIG_PATH}"
    )
    if not os.path.exists(MODELS_CONFIG_PATH):
        raise Exception("The model configuration file does not exist. Please check if the file path is correct.")

    try:
        with open(MODELS_CONFIG_PATH, "r") as f:
            configs = json.load(f)
    except Exception as e:
        raise Exception("The model configuration file format is incorrect. Please check if the content is correct.")

    if not isinstance(configs, list):
        raise Exception(f"The model configuration must be an array, which is actually {type(configs).__name__}.")

    valid_models = []
    for i, model in enumerate(configs, 1):
        if model is None:
            logger.warning(
                "op=model_config_empty_skipped "
                f"index={i}"
            )
            continue

        if not isinstance(model, dict):
            logger.warning(
                "op=model_config_not_dict_skipped "
                f"index={i}"
            )
            continue

        if not model:
            logger.warning(
                "op=model_config_empty_dict_skipped "
                f"index={i}"
            )
            continue

        required_fields = ['name', 'path']
        missing_fields = [field for field in required_fields if field not in model]
        if missing_fields:
            logger.warning(
                "op=model_config_missing_field_skipped "
                f"index={i} "
                f"fields={missing_fields}"
            )
            continue

        logger.debug(
            "op=model_config_find_valid "
            f"name={model['name']} "
            f"path={model['path']}"
        )
        valid_models.append(model)

    logger.info(
        "op=model_config_load_done "
        f"count={len(valid_models)}"
    )

    return valid_models
