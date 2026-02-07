"""Configuration schema and loader for RAGLeakLab.

Re-exports for backward compatibility — old imports such as
``from ragleaklab.config import load_config, HttpTargetConfig``
continue to work.
"""

from ragleaklab.config.load import ConfigError, format_validation_error, load_config
from ragleaklab.config.schema import (
    AttacksConfig,
    Config,
    ConfigRoot,
    CorpusConfig,
    HttpTargetConfig,
    InProcessTargetConfig,
    MockTargetConfig,
    OutputConfig,
    RunConfig,
    ThresholdsConfig,
)

__all__ = [
    "AttacksConfig",
    "Config",
    "ConfigError",
    "ConfigRoot",
    "CorpusConfig",
    "HttpTargetConfig",
    "InProcessTargetConfig",
    "MockTargetConfig",
    "OutputConfig",
    "RunConfig",
    "ThresholdsConfig",
    "format_validation_error",
    "load_config",
]
