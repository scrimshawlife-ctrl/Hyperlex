"""Hugging Face remote-code loader for Hyperlexical (``trust_remote_code=True``).

The checkpoint stores the classify / role / filler heads plus the fine-tuned
encoder layers under ``encoder.<hf_path>``. Frozen trunk layers are not in the
file, so loading first builds ``answerdotai/ModernBERT-base`` (``base_model`` in
config, or ``trunk=`` for a local snapshot), then overlays the checkpoint.

Outputs mirror training: lineage from the CLS state; role/filler logits per
token (pool a word's token states before the heads, as ``infer_model.py`` does).
Lineage probabilities use ``lineage_temperature`` from config. Brier is always
null; this model does not forecast.
"""
from __future__ import annotations

import os

import torch
from torch import nn
from transformers import AutoModel, PretrainedConfig, PreTrainedModel


class HyperlexicalConfig(PretrainedConfig):
    model_type = "hyperlex-encoder"

    def __init__(
        self,
        base_model: str = "answerdotai/ModernBERT-base",
        hidden_size: int = 768,
        id2label: dict | None = None,
        role_vocab: list | None = None,
        filler_vocab: list | None = None,
        lineage_temperature: float = 1.0,
        abstain_threshold: float | None = None,
        **kwargs,
    ):
        super().__init__(id2label=id2label, **kwargs)
        self.base_model = base_model
        self.hidden_size = hidden_size
        self.role_vocab = list(role_vocab or [])
        self.filler_vocab = list(filler_vocab or [])
        self.lineage_temperature = float(lineage_temperature)
        self.abstain_threshold = abstain_threshold


class HyperlexicalModel(PreTrainedModel):
    config_class = HyperlexicalConfig
    base_model_prefix = "encoder"

    def __init__(self, config: HyperlexicalConfig, encoder: nn.Module | None = None):
        super().__init__(config)
        self.encoder = encoder
        self.classify = nn.Linear(config.hidden_size, len(config.id2label))
        self.role_head = nn.Linear(config.hidden_size, len(config.role_vocab))
        self.filler_head = nn.Linear(config.hidden_size, len(config.filler_vocab))

    def _init_weights(self, module):
        pass

    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, *args, trunk: str | None = None, **kwargs):
        from safetensors.torch import load_file

        kwargs.pop("trust_remote_code", None)
        local = kwargs.get("local_files_only", False)
        config = kwargs.pop("config", None) or HyperlexicalConfig.from_pretrained(pretrained_model_name_or_path)
        encoder = AutoModel.from_pretrained(trunk or config.base_model, local_files_only=bool(trunk) or local)
        model = cls(config, encoder=encoder)
        if os.path.isdir(pretrained_model_name_or_path):
            weights = os.path.join(pretrained_model_name_or_path, "model.safetensors")
        else:
            from huggingface_hub import hf_hub_download

            weights = hf_hub_download(pretrained_model_name_or_path, "model.safetensors")
        state = load_file(weights, device="cpu")
        missing, unexpected = model.load_state_dict(state, strict=False)
        heads = {k for k in model.state_dict() if k.split(".", 1)[0] in ("classify", "role_head", "filler_head")}
        if heads & set(missing) or unexpected:
            raise ValueError(f"checkpoint mismatch: missing heads {sorted(heads & set(missing))}, unexpected {unexpected[:5]}")
        return model.eval()

    def forward(self, input_ids=None, attention_mask=None, **kwargs):
        states = self.encoder(input_ids=input_ids, attention_mask=attention_mask, **kwargs).last_hidden_state
        lineage_logits = self.classify(states[:, 0])
        return {
            "last_hidden_state": states,
            "lineage_logits": lineage_logits,
            "lineage_probs": torch.softmax(lineage_logits / self.config.lineage_temperature, dim=-1),
            "role_logits": self.role_head(states),
            "filler_logits": self.filler_head(states),
            "brier": None,
        }
