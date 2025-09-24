import torch
from nemo.collections.nlp.models.language_modeling.megatron_gpt_model import MegatronGPTModel
from nemo.collections.nlp.parts.utils import convert_weights_to_fp32

# Load pretrained BioNeMo GPT model checkpoint
# You must download a compatible .nemo file beforehand
CHECKPOINT_PATH = "models/megatron_bionemo_gpt.nemo"

# Load onto GPU if available
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("🔁 Loading BioNeMo model...")
model = MegatronGPTModel.restore_from(restore_path=CHECKPOINT_PATH, map_location=DEVICE)
model.freeze()

def explain_with_bionemo(prompt: str, max_length: int = 256) -> str:
    tokens = model.tokenizer.text_to_ids(prompt)
    input_tensor = torch.tensor(tokens).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model.generate(
            input_ids=input_tensor,
            max_length=max_length,
            temperature=0.7,
            top_k=40,
            top_p=0.9
        )
    decoded = model.tokenizer.ids_to_text(output[0].cpu().tolist())
    return decoded
