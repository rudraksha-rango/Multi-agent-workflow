import time
from google import genai
from langsmith import traceable
from llm.base_llm import BaseLLM, LLMResponse
from config import config

class GeminiLLM(BaseLLM):
    def __init__(self, model_name="gemini-3.6-flash"):
        if config.GEMINI_API_KEY:
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        else:
            self.client = None
        self.model_name = model_name
        
    @traceable(name="Gemini Generate")
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        if not self.client:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                text=f"[Simulated Gemini Response] for prompt: {prompt[:30]}...",
                input_tokens=len(prompt) // 4,
                output_tokens=50,
                latency_ms=latency,
                model_name=self.model_name,
                estimated_cost=0.0
            )
            
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        latency = (time.time() - start) * 1000
        
        usage = getattr(response, 'usage_metadata', None)
        input_tokens = getattr(usage, 'prompt_token_count', len(prompt) // 4) if usage else len(prompt) // 4
        output_tokens = getattr(usage, 'candidates_token_count', len(response.text) // 4) if usage else len(response.text) // 4
        cost = (input_tokens * self.cost_per_input_token) + (output_tokens * self.cost_per_output_token)
        
        return LLMResponse(
            text=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            model_name=self.model_name,
            estimated_cost=cost
        )
        
    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def cost_per_input_token(self) -> float:
        return 0.000001

    @property
    def cost_per_output_token(self) -> float:
        return 0.000004
