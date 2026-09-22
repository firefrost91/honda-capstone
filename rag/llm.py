"""Pluggable open-source LLM backends.

Four backends, auto-detected in order of how well they run on the machine
they're most likely to be on:

``mlx``           Apple-Silicon native, no server, fastest on an M-series Mac.
``ollama``        The usual local-LLM daemon; used if it is already running.
``llamacpp``      GGUF via llama-cpp-python, for Linux/Windows or CPU-only.
``transformers``  Last resort; works anywhere torch does, slowly.

Every backend is wrapped in the same tiny interface (``available``,
``generate``, ``stream``) so the pipeline never branches on model vendor.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Iterator

from .config import CONFIG, Config


class BaseLLM:
    name = "base"
    available = False

    def generate(self, prompt: str, system: str | None = None,
                 max_tokens: int | None = None, temperature: float | None = None) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, system: str | None = None,
               max_tokens: int | None = None, temperature: float | None = None) -> Iterator[str]:
        yield self.generate(prompt, system, max_tokens, temperature)


class NullLLM(BaseLLM):
    """Retrieval still works without a model; answers become extractive.

    This is deliberately not an error. It keeps the retrieval half of the
    system testable, and makes the failure mode 'here are the passages'
    rather than a stack trace.
    """
    name = "none"
    available = False

    def generate(self, prompt, system=None, max_tokens=None, temperature=None) -> str:
        return ("[No language model is loaded, so this answer is the retrieved evidence "
                "verbatim rather than a synthesis. See the sources below.]")


class MLXLLM(BaseLLM):
    name = "mlx"

    def __init__(self, cfg: Config = CONFIG):
        self.cfg = cfg
        self._model = None
        self._tokenizer = None
        try:
            import mlx_lm  # noqa: F401
            self.available = True
        except ImportError:
            self.available = False

    def _load(self):
        if self._model is None:
            from mlx_lm import load
            self._model, self._tokenizer = load(self.cfg.llm_model)
        return self._model, self._tokenizer

    def _prompt(self, prompt: str, system: str | None) -> str:
        _, tok = self._load()
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def _sampling(self, temperature):
        from mlx_lm.sample_utils import make_sampler, make_logits_processors
        sampler = make_sampler(
            temp=temperature if temperature is not None else self.cfg.temperature,
            top_p=0.9,
        )
        # Small models loop on boilerplate phrasing when summarising many
        # similar passages; a mild penalty over a long window stops that
        # without suppressing legitimately repeated place names.
        processors = make_logits_processors(
            repetition_penalty=1.08, repetition_context_size=256)
        return sampler, processors

    def generate(self, prompt, system=None, max_tokens=None, temperature=None) -> str:
        from mlx_lm import generate as mlx_generate
        model, tok = self._load()
        sampler, processors = self._sampling(temperature)
        return mlx_generate(
            model, tok, prompt=self._prompt(prompt, system),
            max_tokens=max_tokens or self.cfg.max_tokens,
            sampler=sampler, logits_processors=processors, verbose=False,
        ).strip()

    def stream(self, prompt, system=None, max_tokens=None, temperature=None) -> Iterator[str]:
        from mlx_lm import stream_generate
        model, tok = self._load()
        sampler, processors = self._sampling(temperature)
        for resp in stream_generate(
            model, tok, prompt=self._prompt(prompt, system),
            max_tokens=max_tokens or self.cfg.max_tokens,
            sampler=sampler, logits_processors=processors,
        ):
            yield resp.text


class OllamaLLM(BaseLLM):
    name = "ollama"

    def __init__(self, cfg: Config = CONFIG):
        self.cfg = cfg
        self.available = self._ping()

    def _ping(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.cfg.ollama_host}/api/tags", timeout=1.5) as r:
                return r.status == 200
        except Exception:
            return False

    def _post(self, payload: dict, stream: bool):
        req = urllib.request.Request(
            f"{self.cfg.ollama_host}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(req, timeout=600)

    def _messages(self, prompt, system):
        return ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]

    def generate(self, prompt, system=None, max_tokens=None, temperature=None) -> str:
        payload = {
            "model": self.cfg.ollama_model,
            "messages": self._messages(prompt, system),
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.cfg.temperature,
                "num_predict": max_tokens or self.cfg.max_tokens,
            },
        }
        with self._post(payload, stream=False) as r:
            return json.loads(r.read())["message"]["content"].strip()

    def stream(self, prompt, system=None, max_tokens=None, temperature=None) -> Iterator[str]:
        payload = {
            "model": self.cfg.ollama_model,
            "messages": self._messages(prompt, system),
            "stream": True,
            "options": {
                "temperature": temperature if temperature is not None else self.cfg.temperature,
                "num_predict": max_tokens or self.cfg.max_tokens,
            },
        }
        with self._post(payload, stream=True) as r:
            for line in r:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if obj.get("done"):
                    break
                yield obj.get("message", {}).get("content", "")


class LlamaCppLLM(BaseLLM):
    name = "llamacpp"

    def __init__(self, cfg: Config = CONFIG):
        self.cfg = cfg
        self.gguf = os.environ.get("CBRAG_GGUF_PATH", "")
        self._llm = None
        try:
            import llama_cpp  # noqa: F401
            self.available = bool(self.gguf) and os.path.exists(self.gguf)
        except ImportError:
            self.available = False

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama
            self._llm = Llama(model_path=self.gguf, n_ctx=8192, verbose=False)
        return self._llm

    def generate(self, prompt, system=None, max_tokens=None, temperature=None) -> str:
        llm = self._load()
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        out = llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens or self.cfg.max_tokens,
            temperature=temperature if temperature is not None else self.cfg.temperature,
        )
        return out["choices"][0]["message"]["content"].strip()


class TransformersLLM(BaseLLM):
    name = "transformers"

    def __init__(self, cfg: Config = CONFIG):
        self.cfg = cfg
        self.model_id = os.environ.get("CBRAG_HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
        self._pipe = None
        try:
            import transformers  # noqa: F401
            self.available = True
        except ImportError:
            self.available = False

    def _load(self):
        if self._pipe is None:
            from transformers import pipeline
            self._pipe = pipeline("text-generation", model=self.model_id, device_map="auto")
        return self._pipe

    def generate(self, prompt, system=None, max_tokens=None, temperature=None) -> str:
        pipe = self._load()
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        out = pipe(messages, max_new_tokens=max_tokens or self.cfg.max_tokens,
                   temperature=temperature if temperature is not None else self.cfg.temperature,
                   do_sample=True)
        return out[0]["generated_text"][-1]["content"].strip()


_BACKENDS = {
    "mlx": MLXLLM,
    "ollama": OllamaLLM,
    "llamacpp": LlamaCppLLM,
    "transformers": TransformersLLM,
    "none": NullLLM,
}


def get_llm(cfg: Config = CONFIG) -> BaseLLM:
    choice = (cfg.llm_backend or "auto").lower()
    if choice != "auto":
        llm = _BACKENDS.get(choice, NullLLM)(cfg) if choice != "none" else NullLLM()
        return llm
    for name in ("mlx", "ollama", "llamacpp", "transformers"):
        try:
            llm = _BACKENDS[name](cfg)
            if llm.available:
                return llm
        except Exception:
            continue
    return NullLLM()


if __name__ == "__main__":
    llm = get_llm()
    print("backend:", llm.name, "| available:", llm.available)
    if llm.available:
        print(llm.generate("Reply with exactly: RAG backend online.", max_tokens=20))
