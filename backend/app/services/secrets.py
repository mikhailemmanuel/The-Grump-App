from abc import ABC, abstractmethod
import os


class SecretsProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> str: ...


class EnvSecretsProvider(SecretsProvider):
    def get(self, key: str) -> str:
        value = os.environ.get(key, "")
        if not value:
            raise KeyError(f"Secret '{key}' not found in environment")
        return value


class AWSSecretsProvider(SecretsProvider):
    def __init__(self, region: str = "us-east-1"):
        import boto3
        self._client = boto3.client("secretsmanager", region_name=region)
        self._cache: dict[str, str] = {}

    def get(self, key: str) -> str:
        if key not in self._cache:
            resp = self._client.get_secret_value(SecretId=key)
            self._cache[key] = resp["SecretString"]
        return self._cache[key]


def get_secrets_provider() -> SecretsProvider:
    backend = os.environ.get("SECRETS_BACKEND", "env")
    if backend == "aws":
        return AWSSecretsProvider(os.environ.get("AWS_REGION", "us-east-1"))
    return EnvSecretsProvider()
