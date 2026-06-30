# Implement LLM-based Repair bakcend
- Must conform `Repair Algorithm interface`
    - Maybe with some minimal changes

- My idea, use at least 2 different providers
    - GPT@RUB
    - OpenAI 

- INPUT to the LLM/Repair side 
    - => Fault Location

## Prompt Construction 
- Include informations like 
    - Buggy function/ code region aroung the suspected faulthy 
        - QUESTION: How to design 


## GPT RUB -- OpenAI 
- IDEA: Keep single algorithm-level class and push provider variation into an injected,narrower abstaction 


## LLMRepairAlgorithm(RepairAlgorithm)
- Everything provider agnostic

1. Build the prompt from `buggy region + fault location + rank`
2. Parse the model's response into `PatchCandidate` objects in the same format as `TemplateRepairAlgorithm`
    - enforce max_patches/temperature/budget and feeding into the shared ``run_loop.py``


## LLM Client (interface)
- generate completions 
### OpenAICompatibleClient
