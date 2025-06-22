from typing import Protocol

class TranslationGateway(Protocol):
    async def translate(self, text: str, source: str, target: str) -> str:
        ...
