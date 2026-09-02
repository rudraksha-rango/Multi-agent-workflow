import time
from groq import AsyncGroq
from langsmith import traceable
from llm.base_llm import BaseLLM, LLMResponse
from config import config

class GroqLLM(BaseLLM):
    def __init__(self, model_name="openai/gpt-oss-20b"):
        if config.GROQ_API_KEY:
            self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
        else:
            self.client = None
        self.model_name = model_name
        
    @traceable(name="Groq Generate")
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        if not self.client:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                text=f"[Simulated Groq Response] for prompt: {prompt[:30]}...",
                input_tokens=len(prompt) // 4,
                output_tokens=50,
                latency_ms=latency,
                model_name=self.model_name,
                estimated_cost=0.0
            )
            
        chat_completion = await self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model_name,
        )
        latency = (time.time() - start) * 1000
        
        usage = chat_completion.usage
        input_tokens = usage.prompt_tokens if usage else len(prompt) // 4
        output_tokens = usage.completion_tokens if usage else len(chat_completion.choices[0].message.content) // 4
        cost = (input_tokens * self.cost_per_input_token) + (output_tokens * self.cost_per_output_token)
        
        return LLMResponse(
            text=chat_completion.choices[0].message.content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            model_name=self.model_name,
            estimated_cost=cost
        )
        
    @property
    def name(self) -> str:
        return "Groq"

    @property
    def cost_per_input_token(self) -> float:
        return 0.000002

    @property
    def cost_per_output_token(self) -> float:
        return 0.000006
