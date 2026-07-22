from typing import Dict, Any, Tuple
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.validators.payload_validator import PayloadValidator
from app.website_generator.placeholder_engine.engine import PlaceholderEngine
from app.website_generator.utils.logger import generator_logger

class PipelineBuilder:
    """
    Pipeline orchestrator that coordinates the generation pipeline:
    Input -> Validation -> Normalization -> Placeholder Payload -> Builder Queue
    """
    @staticmethod
    def process_pipeline(payload: WebsiteGeneratorPayload) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
        generator_logger.info(f"Pipeline received payload for company: '{payload.businessInfo.companyName}'")

        # Stage 1: Validation
        is_valid, errors = PayloadValidator.validate(payload)
        if not is_valid:
            generator_logger.warning(f"Pipeline validation failed with {len(errors)} errors")
            return False, errors, {}

        # Stage 2: Normalization
        generator_logger.info("Pipeline stage 2: Normalizing payload data...")
        normalized_data = payload.dict()
        normalized_data["businessInfo"]["companyName"] = normalized_data["businessInfo"]["companyName"].strip()

        # Stage 3: Placeholder Engine Payload
        generator_logger.info("Pipeline stage 3: Generating placeholder AST payload...")
        placeholder_meta = PlaceholderEngine.generate_placeholder_payload(payload)

        # Stage 4: Prepared Queue Output
        generator_logger.info("Pipeline stage 4: Pipeline successfully prepared generation payload.")
        return True, {}, {
            "normalized_payload": normalized_data,
            "placeholder_meta": placeholder_meta,
        }
