from src.infrastructure.translation.google_translate_async import google_translate

from .translation_gateway import TranslationGateway


class GoogleTranslationGateway(TranslationGateway):
    async def translate(self, text, source, target):
        return await google_translate(text, source, target)
