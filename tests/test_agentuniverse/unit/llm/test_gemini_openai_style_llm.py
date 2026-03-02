import unittest

from langchain.chains.conversation.base import ConversationChain

import asyncio
from agentuniverse.llm.default.gemini_openai_style_llm import GeminiOpenAIStyleLLM


class TestGeminiOpenAIStyleLLM(unittest.TestCase):
    def setUp(self) -> None:
        self.llm = GeminiOpenAIStyleLLM(model_name='gemini-2.0-flash',
                                        api_key='xxxx',
                                        api_base='https://generativelanguage.googleapis.com/v1beta/openai/',
                                        proxy='http://127.0.0.1:10808')

    def test_call(self) -> None:
        messages = [
            {
                "role": "user",
                "content": "hi, please introduce yourself",
            }
        ]
        output = self.llm.call(messages=messages, streaming=False)
        print(output.__str__())

    def test_acall(self) -> None:
        messages = [
            {
                "role": "user",
                "content": "hi, please introduce yourself",
            }
        ]
        output = asyncio.run(self.llm.acall(messages=messages, streaming=False))
        print(output.__str__())

    def test_call_stream(self):
        messages = [
            {
                "role": "user",
                "content": "hi, please introduce yourself",
            }
        ]
        for chunk in self.llm.call(messages=messages, streaming=True):
            print(chunk.text, end='')
        print()

    #
    def test_acall_stream(self):
        messages = [
            {
                "role": "user",
                "content": "hi, please introduce yourself",
            }
        ]
        asyncio.run(self.call_stream(messages=messages))

    async def call_stream(self, messages: list):

        async for chunk in await self.llm.acall(messages=messages, streaming=True):
            print(chunk, end='')
        print()

    def test_as_langchain(self):
        langchain_llm = self.llm.as_langchain()
        llm_chain = ConversationChain(llm=langchain_llm)
        res = llm_chain.predict(input='hello')
        print(res)

    def test_get_num_tokens(self):
        print(self.llm.get_num_tokens('"content": "hi, please introduce yourself",'))


if __name__ == '__main__':
    unittest.main()
