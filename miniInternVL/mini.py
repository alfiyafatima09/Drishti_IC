"""
MiniInternVL Implementation

A lightweight vision-language model implementation based on InternVL architecture.
Combines a Vision Transformer (ViT) encoder with a Language Model for multimodal tasks.

Reference: https://github.com/OpenGVLab/InternVL
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple, List, Union, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor


# ============================================================
# Configuration Classes
# ============================================================

@dataclass
class VisionConfig:
    """Configuration for the Vision Encoder (InternViT)."""
    image_size: int = 448
    patch_size: int = 14
    hidden_size: int = 1024
    num_hidden_layers: int = 24
    num_attention_heads: int = 16
    intermediate_size: int = 4096
    hidden_act: str = "gelu"
    layer_norm_eps: float = 1e-6
    attention_dropout: float = 0.0
    dropout: float = 0.0
    num_channels: int = 3
    qkv_bias: bool = True
    use_flash_attention: bool = False


@dataclass
class LanguageConfig:
    """Configuration for the Language Model."""
    vocab_size: int = 32000
    hidden_size: int = 2048
    num_hidden_layers: int = 24
    num_attention_heads: int = 16
    num_key_value_heads: int = 16
    intermediate_size: int = 8192
    hidden_act: str = "silu"
    max_position_embeddings: int = 4096
    rms_norm_eps: float = 1e-6
    attention_dropout: float = 0.0
    rope_theta: float = 10000.0
    use_flash_attention: bool = False


@dataclass
class MiniInternVLConfig:
    """Configuration for the full MiniInternVL model."""
    vision_config: VisionConfig = None
    language_config: LanguageConfig = None
    mlp_hidden_size: int = 2048
    num_image_tokens: int = 256
    use_thumbnail: bool = True
    dynamic_image_size: bool = True
    max_dynamic_patch: int = 12
    min_dynamic_patch: int = 1

    def __post_init__(self):
        if self.vision_config is None:
            self.vision_config = VisionConfig()
        if self.language_config is None:
            self.language_config = LanguageConfig()


# ============================================================
# Vision Encoder Components
# ============================================================

class PatchEmbedding(nn.Module):
    """Convert image to patch embeddings."""

    def __init__(self, config: VisionConfig):
        super().__init__()
        self.config = config
        self.num_patches = (config.image_size // config.patch_size) ** 2

        self.projection = nn.Conv2d(
            config.num_channels,
            config.hidden_size,
            kernel_size=config.patch_size,
            stride=config.patch_size
        )

    def forward(self, pixel_values: Tensor) -> Tensor:
        """
        Args:
            pixel_values: (batch, channels, height, width)
        Returns:
            (batch, num_patches, hidden_size)
        """
        x = self.projection(pixel_values)  # (B, hidden_size, H/P, W/P)
        x = x.flatten(2).transpose(1, 2)   # (B, num_patches, hidden_size)
        return x


class VisionAttention(nn.Module):
    """Multi-head self-attention for vision encoder."""

    def __init__(self, config: VisionConfig):
        super().__init__()
        self.config = config
        self.num_heads = config.num_attention_heads
        self.head_dim = config.hidden_size // config.num_attention_heads
        self.scale = self.head_dim ** -0.5

        self.qkv = nn.Linear(
            config.hidden_size,
            config.hidden_size * 3,
            bias=config.qkv_bias
        )
        self.proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.attention_dropout = nn.Dropout(config.attention_dropout)

    def forward(
        self,
        hidden_states: Tensor,
        attention_mask: Optional[Tensor] = None
    ) -> Tensor:
        batch_size, seq_len, _ = hidden_states.shape

        # QKV projection
        qkv = self.qkv(hidden_states)
        qkv = qkv.reshape(batch_size, seq_len, 3, self.num_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, B, num_heads, seq_len, head_dim)
        q, k, v = qkv[0], qkv[1], qkv[2]

        # Attention scores
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if attention_mask is not None:
            attn_weights = attn_weights + attention_mask

        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.attention_dropout(attn_weights)

        # Attention output
        attn_output = torch.matmul(attn_weights, v)
        attn_output = attn_output.transpose(1, 2).reshape(batch_size, seq_len, -1)
        attn_output = self.proj(attn_output)

        return attn_output


class VisionMLP(nn.Module):
    """MLP block for vision encoder."""

    def __init__(self, config: VisionConfig):
        super().__init__()
        self.fc1 = nn.Linear(config.hidden_size, config.intermediate_size)
        self.fc2 = nn.Linear(config.intermediate_size, config.hidden_size)
        self.act = self._get_activation(config.hidden_act)
        self.dropout = nn.Dropout(config.dropout)

    def _get_activation(self, act_name: str):
        if act_name == "gelu":
            return nn.GELU()
        elif act_name == "relu":
            return nn.ReLU()
        elif act_name == "silu":
            return nn.SiLU()
        else:
            raise ValueError(f"Unknown activation: {act_name}")

    def forward(self, hidden_states: Tensor) -> Tensor:
        hidden_states = self.fc1(hidden_states)
        hidden_states = self.act(hidden_states)
        hidden_states = self.dropout(hidden_states)
        hidden_states = self.fc2(hidden_states)
        hidden_states = self.dropout(hidden_states)
        return hidden_states


class VisionEncoderLayer(nn.Module):
    """Single transformer layer for vision encoder."""

    def __init__(self, config: VisionConfig):
        super().__init__()
        self.attention = VisionAttention(config)
        self.mlp = VisionMLP(config)
        self.layernorm1 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.layernorm2 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

    def forward(
        self,
        hidden_states: Tensor,
        attention_mask: Optional[Tensor] = None
    ) -> Tensor:
        # Self-attention with residual
        residual = hidden_states
        hidden_states = self.layernorm1(hidden_states)
        hidden_states = self.attention(hidden_states, attention_mask)
        hidden_states = residual + hidden_states

        # MLP with residual
        residual = hidden_states
        hidden_states = self.layernorm2(hidden_states)
        hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states

        return hidden_states


class InternViT(nn.Module):
    """
    InternViT Vision Encoder.

    A Vision Transformer that extracts visual features from images.
    """

    def __init__(self, config: VisionConfig):
        super().__init__()
        self.config = config

        self.patch_embedding = PatchEmbedding(config)
        num_patches = self.patch_embedding.num_patches

        # CLS token and position embeddings
        self.cls_token = nn.Parameter(torch.zeros(1, 1, config.hidden_size))
        self.position_embedding = nn.Parameter(
            torch.zeros(1, num_patches + 1, config.hidden_size)
        )
        self.dropout = nn.Dropout(config.dropout)

        # Transformer layers
        self.layers = nn.ModuleList([
            VisionEncoderLayer(config) for _ in range(config.num_hidden_layers)
        ])

        self.layernorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

        self._init_weights()

    def _init_weights(self):
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.position_embedding, std=0.02)

    def forward(
        self,
        pixel_values: Tensor,
        attention_mask: Optional[Tensor] = None,
        output_hidden_states: bool = False
    ) -> Union[Tensor, Tuple[Tensor, List[Tensor]]]:
        batch_size = pixel_values.shape[0]

        # Patch embedding
        hidden_states = self.patch_embedding(pixel_values)

        # Add CLS token
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        hidden_states = torch.cat([cls_tokens, hidden_states], dim=1)

        # Add position embedding
        hidden_states = hidden_states + self.position_embedding
        hidden_states = self.dropout(hidden_states)

        # Transformer layers
        all_hidden_states = [] if output_hidden_states else None

        for layer in self.layers:
            if output_hidden_states:
                all_hidden_states.append(hidden_states)
            hidden_states = layer(hidden_states, attention_mask)

        hidden_states = self.layernorm(hidden_states)

        if output_hidden_states:
            all_hidden_states.append(hidden_states)
            return hidden_states, all_hidden_states

        return hidden_states


# ============================================================
# Language Model Components
# ============================================================

class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization."""

    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, hidden_states: Tensor) -> Tensor:
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.eps)
        return self.weight * hidden_states


class RotaryEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE)."""

    def __init__(self, dim: int, max_position_embeddings: int = 4096, base: float = 10000.0):
        super().__init__()
        self.dim = dim
        self.max_position_embeddings = max_position_embeddings
        self.base = base

        inv_freq = 1.0 / (self.base ** (torch.arange(0, self.dim, 2).float() / self.dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    def forward(self, x: Tensor, seq_len: int) -> Tuple[Tensor, Tensor]:
        t = torch.arange(seq_len, device=x.device, dtype=self.inv_freq.dtype)
        freqs = torch.einsum("i,j->ij", t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        return emb.cos(), emb.sin()


def rotate_half(x: Tensor) -> Tensor:
    """Rotate half the hidden dims of the input."""
    x1, x2 = x[..., :x.shape[-1] // 2], x[..., x.shape[-1] // 2:]
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(q: Tensor, k: Tensor, cos: Tensor, sin: Tensor) -> Tuple[Tensor, Tensor]:
    """Apply rotary position embeddings to query and key tensors."""
    cos = cos.unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, dim)
    sin = sin.unsqueeze(0).unsqueeze(0)
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed, k_embed


class LanguageAttention(nn.Module):
    """Multi-head attention for language model with GQA support."""

    def __init__(self, config: LanguageConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.num_key_value_heads = config.num_key_value_heads
        self.head_dim = self.hidden_size // self.num_heads
        self.num_key_value_groups = self.num_heads // self.num_key_value_heads

        self.q_proj = nn.Linear(self.hidden_size, self.num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(self.num_heads * self.head_dim, self.hidden_size, bias=False)

        self.rotary_emb = RotaryEmbedding(
            self.head_dim,
            max_position_embeddings=config.max_position_embeddings,
            base=config.rope_theta
        )
        self.attention_dropout = nn.Dropout(config.attention_dropout)

    def forward(
        self,
        hidden_states: Tensor,
        attention_mask: Optional[Tensor] = None,
        position_ids: Optional[Tensor] = None,
        past_key_value: Optional[Tuple[Tensor, Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[Tensor, Optional[Tuple[Tensor, Tensor]]]:
        batch_size, seq_len, _ = hidden_states.shape

        # QKV projections
        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        # Reshape
        query_states = query_states.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(batch_size, seq_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(batch_size, seq_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        # Apply rotary embeddings
        cos, sin = self.rotary_emb(value_states, seq_len)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        # Handle KV cache
        if past_key_value is not None:
            key_states = torch.cat([past_key_value[0], key_states], dim=2)
            value_states = torch.cat([past_key_value[1], value_states], dim=2)

        past_key_value = (key_states, value_states) if use_cache else None

        # Repeat KV for GQA
        if self.num_key_value_groups > 1:
            key_states = key_states.repeat_interleave(self.num_key_value_groups, dim=1)
            value_states = value_states.repeat_interleave(self.num_key_value_groups, dim=1)

        # Attention
        attn_weights = torch.matmul(query_states, key_states.transpose(-2, -1)) / math.sqrt(self.head_dim)

        if attention_mask is not None:
            attn_weights = attn_weights + attention_mask

        attn_weights = F.softmax(attn_weights, dim=-1, dtype=torch.float32).to(query_states.dtype)
        attn_weights = self.attention_dropout(attn_weights)

        attn_output = torch.matmul(attn_weights, value_states)
        attn_output = attn_output.transpose(1, 2).reshape(batch_size, seq_len, -1)
        attn_output = self.o_proj(attn_output)

        return attn_output, past_key_value


class LanguageMLP(nn.Module):
    """MLP block for language model with SwiGLU activation."""

    def __init__(self, config: LanguageConfig):
        super().__init__()
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.up_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size, bias=False)
        self.act = nn.SiLU()

    def forward(self, hidden_states: Tensor) -> Tensor:
        return self.down_proj(self.act(self.gate_proj(hidden_states)) * self.up_proj(hidden_states))


class LanguageDecoderLayer(nn.Module):
    """Single transformer decoder layer."""

    def __init__(self, config: LanguageConfig):
        super().__init__()
        self.self_attn = LanguageAttention(config)
        self.mlp = LanguageMLP(config)
        self.input_layernorm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.post_attention_layernorm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)

    def forward(
        self,
        hidden_states: Tensor,
        attention_mask: Optional[Tensor] = None,
        position_ids: Optional[Tensor] = None,
        past_key_value: Optional[Tuple[Tensor, Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[Tensor, Optional[Tuple[Tensor, Tensor]]]:
        # Self-attention
        residual = hidden_states
        hidden_states = self.input_layernorm(hidden_states)
        hidden_states, present_key_value = self.self_attn(
            hidden_states,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_value=past_key_value,
            use_cache=use_cache
        )
        hidden_states = residual + hidden_states

        # MLP
        residual = hidden_states
        hidden_states = self.post_attention_layernorm(hidden_states)
        hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states

        return hidden_states, present_key_value


class LanguageModel(nn.Module):
    """Causal Language Model (decoder-only transformer)."""

    def __init__(self, config: LanguageConfig):
        super().__init__()
        self.config = config

        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)
        self.layers = nn.ModuleList([
            LanguageDecoderLayer(config) for _ in range(config.num_hidden_layers)
        ])
        self.norm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)

    def forward(
        self,
        input_ids: Optional[Tensor] = None,
        inputs_embeds: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
        position_ids: Optional[Tensor] = None,
        past_key_values: Optional[List[Tuple[Tensor, Tensor]]] = None,
        use_cache: bool = False
    ) -> Tuple[Tensor, Optional[List[Tuple[Tensor, Tensor]]]]:
        if inputs_embeds is None:
            inputs_embeds = self.embed_tokens(input_ids)

        hidden_states = inputs_embeds

        # Prepare attention mask
        if attention_mask is not None:
            batch_size, seq_len = hidden_states.shape[:2]
            # Create causal mask
            causal_mask = torch.triu(
                torch.full((seq_len, seq_len), float("-inf"), device=hidden_states.device),
                diagonal=1
            )
            attention_mask = causal_mask.unsqueeze(0).unsqueeze(0)

        # Decoder layers
        present_key_values = [] if use_cache else None

        for i, layer in enumerate(self.layers):
            past_key_value = past_key_values[i] if past_key_values is not None else None
            hidden_states, present_key_value = layer(
                hidden_states,
                attention_mask=attention_mask,
                position_ids=position_ids,
                past_key_value=past_key_value,
                use_cache=use_cache
            )
            if use_cache:
                present_key_values.append(present_key_value)

        hidden_states = self.norm(hidden_states)

        return hidden_states, present_key_values


# ============================================================
# Vision-Language Connector
# ============================================================

class MLPProjector(nn.Module):
    """MLP projector to align vision and language features."""

    def __init__(
        self,
        vision_hidden_size: int,
        language_hidden_size: int,
        mlp_hidden_size: int
    ):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(vision_hidden_size, mlp_hidden_size),
            nn.GELU(),
            nn.Linear(mlp_hidden_size, language_hidden_size)
        )

    def forward(self, vision_features: Tensor) -> Tensor:
        return self.mlp(vision_features)


class PixelShuffle(nn.Module):
    """Pixel shuffle for downsampling visual tokens."""

    def __init__(self, scale_factor: int = 2):
        super().__init__()
        self.scale_factor = scale_factor

    def forward(self, x: Tensor) -> Tensor:
        """
        Args:
            x: (batch, seq_len, hidden_size)
        Returns:
            (batch, seq_len/scale^2, hidden_size*scale^2)
        """
        batch_size, seq_len, hidden_size = x.shape
        h = w = int(math.sqrt(seq_len))

        x = x.view(batch_size, h, w, hidden_size)
        x = x.view(batch_size, h // self.scale_factor, self.scale_factor,
                   w // self.scale_factor, self.scale_factor, hidden_size)
        x = x.permute(0, 1, 3, 2, 4, 5).contiguous()
        x = x.view(batch_size, -1, hidden_size * self.scale_factor * self.scale_factor)

        return x


# ============================================================
# Main MiniInternVL Model
# ============================================================

class MiniInternVL(nn.Module):
    """
    MiniInternVL: A Vision-Language Model.

    Combines InternViT vision encoder with a language model for multimodal understanding.

    Architecture:
    - Vision Encoder: InternViT
    - Vision-Language Connector: MLP Projector with optional Pixel Shuffle
    - Language Model: Decoder-only Transformer (LLaMA-style)
    """

    def __init__(self, config: MiniInternVLConfig):
        super().__init__()
        self.config = config

        # Vision encoder
        self.vision_encoder = InternViT(config.vision_config)

        # Pixel shuffle for token reduction
        self.pixel_shuffle = PixelShuffle(scale_factor=2)

        # Vision-language projector
        vision_hidden = config.vision_config.hidden_size * 4  # After pixel shuffle
        self.mlp_projector = MLPProjector(
            vision_hidden_size=vision_hidden,
            language_hidden_size=config.language_config.hidden_size,
            mlp_hidden_size=config.mlp_hidden_size
        )

        # Language model
        self.language_model = LanguageModel(config.language_config)

        # LM head
        self.lm_head = nn.Linear(
            config.language_config.hidden_size,
            config.language_config.vocab_size,
            bias=False
        )

        # Special token IDs
        self.image_token_id = 32000  # Placeholder
        self.pad_token_id = 0

    def get_vision_features(self, pixel_values: Tensor) -> Tensor:
        """Extract and project vision features."""
        # Get vision encoder output
        vision_output = self.vision_encoder(pixel_values)

        # Remove CLS token and apply pixel shuffle
        vision_features = vision_output[:, 1:, :]  # Remove CLS
        vision_features = self.pixel_shuffle(vision_features)

        # Project to language model space
        vision_features = self.mlp_projector(vision_features)

        return vision_features

    def merge_vision_language_embeddings(
        self,
        input_ids: Tensor,
        vision_features: Tensor,
        attention_mask: Optional[Tensor] = None
    ) -> Tuple[Tensor, Optional[Tensor]]:
        """Merge vision and language embeddings at image token positions."""
        batch_size, seq_len = input_ids.shape

        # Get text embeddings
        text_embeds = self.language_model.embed_tokens(input_ids)

        # Find image token positions
        image_mask = input_ids == self.image_token_id

        # Create merged embeddings
        merged_embeds = text_embeds.clone()

        for batch_idx in range(batch_size):
            image_positions = torch.where(image_mask[batch_idx])[0]
            if len(image_positions) > 0:
                num_vision_tokens = vision_features.shape[1]
                start_pos = image_positions[0].item()
                end_pos = min(start_pos + num_vision_tokens, seq_len)
                actual_tokens = end_pos - start_pos
                merged_embeds[batch_idx, start_pos:end_pos] = vision_features[batch_idx, :actual_tokens]

        return merged_embeds, attention_mask

    def forward(
        self,
        pixel_values: Optional[Tensor] = None,
        input_ids: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
        labels: Optional[Tensor] = None,
        past_key_values: Optional[List[Tuple[Tensor, Tensor]]] = None,
        use_cache: bool = False,
        return_dict: bool = True
    ) -> Dict[str, Any]:
        """
        Forward pass for MiniInternVL.

        Args:
            pixel_values: Image tensor (batch, channels, height, width)
            input_ids: Token IDs (batch, seq_len)
            attention_mask: Attention mask (batch, seq_len)
            labels: Labels for language modeling loss (batch, seq_len)
            past_key_values: KV cache for generation
            use_cache: Whether to return KV cache
            return_dict: Whether to return a dictionary

        Returns:
            Dictionary containing logits, loss, and optional KV cache
        """
        # Get vision features if images provided
        vision_features = None
        if pixel_values is not None:
            vision_features = self.get_vision_features(pixel_values)

        # Prepare inputs
        if vision_features is not None and input_ids is not None:
            inputs_embeds, attention_mask = self.merge_vision_language_embeddings(
                input_ids, vision_features, attention_mask
            )
            input_ids = None
        else:
            inputs_embeds = None

        # Language model forward
        hidden_states, present_key_values = self.language_model(
            input_ids=input_ids,
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            past_key_values=past_key_values,
            use_cache=use_cache
        )

        # LM head
        logits = self.lm_head(hidden_states)

        # Compute loss if labels provided
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
                ignore_index=-100
            )

        if return_dict:
            return {
                "loss": loss,
                "logits": logits,
                "past_key_values": present_key_values,
                "hidden_states": hidden_states
            }

        return logits, loss, present_key_values

    @torch.no_grad()
    def generate(
        self,
        pixel_values: Optional[Tensor] = None,
        input_ids: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
        max_new_tokens: int = 512,
        temperature: float = 1.0,
        top_p: float = 0.9,
        top_k: int = 50,
        do_sample: bool = True,
        eos_token_id: int = 2,
        pad_token_id: int = 0
    ) -> Tensor:
        """
        Generate text given an image and/or text prompt.

        Args:
            pixel_values: Image tensor
            input_ids: Initial token IDs
            attention_mask: Attention mask
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            do_sample: Whether to sample or use greedy decoding
            eos_token_id: End of sequence token ID
            pad_token_id: Padding token ID

        Returns:
            Generated token IDs
        """
        # Get vision features
        vision_features = None
        if pixel_values is not None:
            vision_features = self.get_vision_features(pixel_values)

        # Prepare initial embeddings
        if vision_features is not None and input_ids is not None:
            inputs_embeds, attention_mask = self.merge_vision_language_embeddings(
                input_ids, vision_features, attention_mask
            )
            current_ids = input_ids.clone()
        else:
            inputs_embeds = self.language_model.embed_tokens(input_ids)
            current_ids = input_ids.clone()

        past_key_values = None

        # Generation loop
        for _ in range(max_new_tokens):
            # Forward pass
            hidden_states, past_key_values = self.language_model(
                inputs_embeds=inputs_embeds if past_key_values is None else None,
                input_ids=current_ids[:, -1:] if past_key_values is not None else None,
                past_key_values=past_key_values,
                use_cache=True
            )

            # Get logits for last position
            logits = self.lm_head(hidden_states[:, -1, :])

            # Apply temperature
            if temperature > 0:
                logits = logits / temperature

            # Sample or greedy
            if do_sample:
                # Top-k filtering
                if top_k > 0:
                    indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
                    logits[indices_to_remove] = float("-inf")

                # Top-p filtering
                if top_p < 1.0:
                    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = 0
                    indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                    logits[indices_to_remove] = float("-inf")

                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                next_token = logits.argmax(dim=-1, keepdim=True)

            current_ids = torch.cat([current_ids, next_token], dim=-1)

            # Check for EOS
            if (next_token == eos_token_id).all():
                break

        return current_ids

    @classmethod
    def from_pretrained(cls, model_path: str, device: str = "cuda") -> "MiniInternVL":
        """Load a pretrained MiniInternVL model."""
        import json
        from pathlib import Path

        model_path = Path(model_path)

        # Load config
        config_path = model_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config_dict = json.load(f)
            config = MiniInternVLConfig(
                vision_config=VisionConfig(**config_dict.get("vision_config", {})),
                language_config=LanguageConfig(**config_dict.get("language_config", {})),
                **{k: v for k, v in config_dict.items() if k not in ["vision_config", "language_config"]}
            )
        else:
            config = MiniInternVLConfig()

        # Create model
        model = cls(config)

        # Load weights
        weights_path = model_path / "pytorch_model.bin"
        if weights_path.exists():
            state_dict = torch.load(weights_path, map_location=device)
            model.load_state_dict(state_dict, strict=False)

        return model.to(device)

    def save_pretrained(self, save_path: str):
        """Save model weights and config."""
        import json
        from pathlib import Path

        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save config
        config_dict = {
            "vision_config": self.config.vision_config.__dict__,
            "language_config": self.config.language_config.__dict__,
            "mlp_hidden_size": self.config.mlp_hidden_size,
            "num_image_tokens": self.config.num_image_tokens,
        }
        with open(save_path / "config.json", "w") as f:
            json.dump(config_dict, f, indent=2)

        # Save weights
        torch.save(self.state_dict(), save_path / "pytorch_model.bin")


# ============================================================
# Image Preprocessing
# ============================================================

class ImageProcessor:
    """Image preprocessor for MiniInternVL."""

    def __init__(
        self,
        image_size: int = 448,
        mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
        std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    ):
        self.image_size = image_size
        self.mean = torch.tensor(mean).view(1, 3, 1, 1)
        self.std = torch.tensor(std).view(1, 3, 1, 1)

    def preprocess(self, images: Union[Tensor, List[Tensor]]) -> Tensor:
        """
        Preprocess images for the model.

        Args:
            images: PIL images or tensor (batch, C, H, W) in range [0, 255]

        Returns:
            Normalized tensor (batch, C, image_size, image_size)
        """
        if isinstance(images, list):
            images = torch.stack(images)

        # Resize
        images = F.interpolate(
            images.float(),
            size=(self.image_size, self.image_size),
            mode="bilinear",
            align_corners=False
        )

        # Normalize to [0, 1]
        images = images / 255.0

        # Apply ImageNet normalization
        images = (images - self.mean.to(images.device)) / self.std.to(images.device)

        return images


# ============================================================
# Convenience Functions
# ============================================================

def create_mini_internvl(
    vision_hidden_size: int = 1024,
    language_hidden_size: int = 2048,
    num_vision_layers: int = 24,
    num_language_layers: int = 24,
    vocab_size: int = 32000,
    image_size: int = 448
) -> MiniInternVL:
    """
    Create a MiniInternVL model with custom configuration.

    Args:
        vision_hidden_size: Hidden size for vision encoder
        language_hidden_size: Hidden size for language model
        num_vision_layers: Number of vision transformer layers
        num_language_layers: Number of language transformer layers
        vocab_size: Vocabulary size
        image_size: Input image size

    Returns:
        Configured MiniInternVL model
    """
    vision_config = VisionConfig(
        hidden_size=vision_hidden_size,
        num_hidden_layers=num_vision_layers,
        image_size=image_size
    )

    language_config = LanguageConfig(
        hidden_size=language_hidden_size,
        num_hidden_layers=num_language_layers,
        vocab_size=vocab_size
    )

    config = MiniInternVLConfig(
        vision_config=vision_config,
        language_config=language_config
    )

    return MiniInternVL(config)


if __name__ == "__main__":
    # Example usage
    print("Creating MiniInternVL model...")

    # Create model
    model = create_mini_internvl(
        vision_hidden_size=768,
        language_hidden_size=1024,
        num_vision_layers=12,
        num_language_layers=12,
        vocab_size=32000,
        image_size=224
    )

    # Print model info
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params / 1e6:.2f}M")

    # Example forward pass
    batch_size = 2
    pixel_values = torch.randn(batch_size, 3, 224, 224)
    input_ids = torch.randint(0, 32000, (batch_size, 64))

    print("Running forward pass...")
    output = model(pixel_values=pixel_values, input_ids=input_ids)
    print(f"Output logits shape: {output['logits'].shape}")

    print("MiniInternVL model created successfully!")
