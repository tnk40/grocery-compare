---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:15720
- loss:ContrastiveLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: Fairy Fabric Conditioner for Sensitive Skin 85W
  sentences:
  - Crownless Pineapple
  - 2 British Lamb Loin Chops
  - Biotiful Gut Health Kefir Natural Yogurt Original 1kg
- source_sentence: Sliced Beetroot in Vinegar 440g
  sentences:
  - Tuna Chunks in Brine 4x145g
  - Seabrook Sea Salt Crisps 6 Pack
  - Bunched Beetroot 500g
- source_sentence: Greek Yoghurt 0% Fat
  sentences:
  - British Mild Cheddar Cheese Slices 240g
  - Frozen Sweetcorn
  - Danone Skyr Icelandic Style Yoghurt 450g
- source_sentence: Arborio Rice
  sentences:
  - Highland Spring Still Water
  - Tagliatelle 500g
  - itsu Satay Rice Noodle Pot 64g
- source_sentence: Alta Rica 100% Arabica Instant Coffee
  sentences:
  - Lurpak Unsalted Butter 200g
  - Sour Cream & Chive Snack Mix Sharing Crisps
  - Nescafe Cappuccino Instant Coffee Sachets 12x15.5g
pipeline_tag: sentence-similarity
library_name: sentence-transformers
metrics:
- cosine_accuracy
- cosine_accuracy_threshold
- cosine_f1
- cosine_f1_threshold
- cosine_precision
- cosine_recall
- cosine_ap
- cosine_mcc
model-index:
- name: SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2
  results:
  - task:
      type: binary-classification
      name: Binary Classification
    dataset:
      name: grocery matching
      type: grocery-matching
    metrics:
    - type: cosine_accuracy
      value: 0.8094632409056219
      name: Cosine Accuracy
    - type: cosine_accuracy_threshold
      value: 0.891746997833252
      name: Cosine Accuracy Threshold
    - type: cosine_f1
      value: 0.6973635350909766
      name: Cosine F1
    - type: cosine_f1_threshold
      value: 0.7923517823219299
      name: Cosine F1 Threshold
    - type: cosine_precision
      value: 0.6081606217616581
      name: Cosine Precision
    - type: cosine_recall
      value: 0.8172323759791122
      name: Cosine Recall
    - type: cosine_ap
      value: 0.6444283706313365
      name: Cosine Ap
    - type: cosine_mcc
      value: 0.5585580802588833
      name: Cosine Mcc
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for retrieval.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'BertModel'})
  (1): Pooling({'embedding_dimension': 384, 'pooling_mode': 'mean', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'Alta Rica 100% Arabica Instant Coffee',
    'Nescafe Cappuccino Instant Coffee Sachets 12x15.5g',
    'Lurpak Unsalted Butter 200g',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.4758, 0.3379],
#         [0.4758, 1.0000, 0.5169],
#         [0.3379, 0.5169, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Binary Classification

* Dataset: `grocery-matching`
* Evaluated with [<code>BinaryClassificationEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.sentence_transformer.evaluation.BinaryClassificationEvaluator)

| Metric                    | Value      |
|:--------------------------|:-----------|
| cosine_accuracy           | 0.8095     |
| cosine_accuracy_threshold | 0.8917     |
| cosine_f1                 | 0.6974     |
| cosine_f1_threshold       | 0.7924     |
| cosine_precision          | 0.6082     |
| cosine_recall             | 0.8172     |
| **cosine_ap**             | **0.6444** |
| cosine_mcc                | 0.5586     |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 15,720 training samples
* Columns: <code>sentence1</code>, <code>sentence2</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence1                                                                        | sentence2                                                                         | label                                                         |
  |:--------|:---------------------------------------------------------------------------------|:----------------------------------------------------------------------------------|:--------------------------------------------------------------|
  | type    | string                                                                           | string                                                                            | float                                                         |
  | details | <ul><li>min: 3 tokens</li><li>mean: 9.36 tokens</li><li>max: 25 tokens</li></ul> | <ul><li>min: 3 tokens</li><li>mean: 10.38 tokens</li><li>max: 23 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.3</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence1                                                 | sentence2                                                        | label            |
  |:----------------------------------------------------------|:-----------------------------------------------------------------|:-----------------|
  | <code>Apple & Pear Juice, Not From Concentrate 1L</code>  | <code>innocent Pure Apple Fruit Juice Family Size</code>         | <code>1.0</code> |
  | <code>Extra Strong 80 Tea Bags 232g</code>                | <code>Napolina Linguine Pasta</code>                             | <code>0.0</code> |
  | <code>Caramelised Red Onion Flavoured Pork Burgers</code> | <code>Wood-Fired Four Cheese & Caramelised Red Onion, ...</code> | <code>1.0</code> |
* Loss: [<code>ContrastiveLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#contrastiveloss) with these parameters:
  ```json
  {
      "distance_metric": "SiameseDistanceMetric.EUCLIDEAN",
      "margin": 1.0,
      "size_average": true
  }
  ```

### Evaluation Dataset

#### Unnamed Dataset

* Size: 3,931 evaluation samples
* Columns: <code>sentence1</code>, <code>sentence2</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence1                                                                        | sentence2                                                                         | label                                                          |
  |:--------|:---------------------------------------------------------------------------------|:----------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                           | string                                                                            | float                                                          |
  | details | <ul><li>min: 3 tokens</li><li>mean: 9.54 tokens</li><li>max: 25 tokens</li></ul> | <ul><li>min: 3 tokens</li><li>mean: 10.44 tokens</li><li>max: 23 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.29</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence1                                                  | sentence2                                                    | label            |
  |:-----------------------------------------------------------|:-------------------------------------------------------------|:-----------------|
  | <code>Plain Flour</code>                                   | <code>Doves Farm Organic White Self Raising Flour 1kg</code> | <code>0.0</code> |
  | <code>Succulent Boneless Chicken Thigh Fillets 650g</code> | <code>Shazans Chicken Thighs 1kg</code>                      | <code>0.0</code> |
  | <code>Petite Plum Vine Tomatoes 220g</code>                | <code>Cherry on the Vine Tomatoes 200g</code>                | <code>1.0</code> |
* Loss: [<code>ContrastiveLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#contrastiveloss) with these parameters:
  ```json
  {
      "distance_metric": "SiameseDistanceMetric.EUCLIDEAN",
      "margin": 1.0,
      "size_average": true
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 32
- `num_train_epochs`: 5
- `learning_rate`: 2e-05
- `warmup_steps`: 0.1
- `per_device_eval_batch_size`: 32

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 32
- `num_train_epochs`: 5
- `max_steps`: -1
- `learning_rate`: 2e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0.1
- `optim`: adamw_torch_fused
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1.0
- `label_smoothing_factor`: 0.0
- `bf16`: False
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: trackio
- `per_device_eval_batch_size`: 32
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: []
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `warmup_ratio`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch  | Step | Training Loss | Validation Loss | grocery-matching_cosine_ap |
|:------:|:----:|:-------------:|:---------------:|:--------------------------:|
| 0.1016 | 50   | 0.1256        | -               | -                          |
| 0.2033 | 100  | 0.1053        | -               | -                          |
| 0.3049 | 150  | 0.0967        | -               | -                          |
| 0.4065 | 200  | 0.0930        | -               | -                          |
| 0.5081 | 250  | 0.0885        | -               | -                          |
| 0.6098 | 300  | 0.0875        | -               | -                          |
| 0.7114 | 350  | 0.0897        | -               | -                          |
| 0.8130 | 400  | 0.0824        | -               | -                          |
| 0.9146 | 450  | 0.0852        | -               | -                          |
| 1.0    | 492  | -             | 0.0863          | 0.5357                     |
| 1.0163 | 500  | 0.0807        | -               | -                          |
| 1.1179 | 550  | 0.0775        | -               | -                          |
| 1.2195 | 600  | 0.0815        | -               | -                          |
| 1.3211 | 650  | 0.0753        | -               | -                          |
| 1.4228 | 700  | 0.0746        | -               | -                          |
| 1.5244 | 750  | 0.0792        | -               | -                          |
| 1.6260 | 800  | 0.0794        | -               | -                          |
| 1.7276 | 850  | 0.0715        | -               | -                          |
| 1.8293 | 900  | 0.0737        | -               | -                          |
| 1.9309 | 950  | 0.0760        | -               | -                          |
| 2.0    | 984  | -             | 0.0775          | 0.5922                     |
| 2.0325 | 1000 | 0.0691        | -               | -                          |
| 2.1341 | 1050 | 0.0681        | -               | -                          |
| 2.2358 | 1100 | 0.0666        | -               | -                          |
| 2.3374 | 1150 | 0.0693        | -               | -                          |
| 2.4390 | 1200 | 0.0658        | -               | -                          |
| 2.5407 | 1250 | 0.0690        | -               | -                          |
| 2.6423 | 1300 | 0.0683        | -               | -                          |
| 2.7439 | 1350 | 0.0698        | -               | -                          |
| 2.8455 | 1400 | 0.0692        | -               | -                          |
| 2.9472 | 1450 | 0.0702        | -               | -                          |
| 3.0    | 1476 | -             | 0.0727          | 0.6215                     |
| 3.0488 | 1500 | 0.0680        | -               | -                          |
| 3.1504 | 1550 | 0.0647        | -               | -                          |
| 3.2520 | 1600 | 0.0656        | -               | -                          |
| 3.3537 | 1650 | 0.0634        | -               | -                          |
| 3.4553 | 1700 | 0.0622        | -               | -                          |
| 3.5569 | 1750 | 0.0606        | -               | -                          |
| 3.6585 | 1800 | 0.0662        | -               | -                          |
| 3.7602 | 1850 | 0.0611        | -               | -                          |
| 3.8618 | 1900 | 0.0595        | -               | -                          |
| 3.9634 | 1950 | 0.0661        | -               | -                          |
| 4.0    | 1968 | -             | 0.0707          | 0.6397                     |
| 4.0650 | 2000 | 0.0621        | -               | -                          |
| 4.1667 | 2050 | 0.0650        | -               | -                          |
| 4.2683 | 2100 | 0.0610        | -               | -                          |
| 4.3699 | 2150 | 0.0571        | -               | -                          |
| 4.4715 | 2200 | 0.0596        | -               | -                          |
| 4.5732 | 2250 | 0.0590        | -               | -                          |
| 4.6748 | 2300 | 0.0640        | -               | -                          |
| 4.7764 | 2350 | 0.0623        | -               | -                          |
| 4.8780 | 2400 | 0.0591        | -               | -                          |
| 4.9797 | 2450 | 0.0571        | -               | -                          |
| 5.0    | 2460 | -             | 0.0690          | 0.6444                     |


### Training Time
- **Training**: 2.0 minutes
- **Evaluation**: 12.6 seconds
- **Total**: 2.2 minutes

### Framework Versions
- Python: 3.11.5
- Sentence Transformers: 5.4.1
- Transformers: 5.5.4
- PyTorch: 2.11.0
- Accelerate: 1.13.0
- Datasets: 4.8.4
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

#### ContrastiveLoss
```bibtex
@inproceedings{hadsell2006dimensionality,
    author={Hadsell, R. and Chopra, S. and LeCun, Y.},
    booktitle={2006 IEEE Computer Society Conference on Computer Vision and Pattern Recognition (CVPR'06)},
    title={Dimensionality Reduction by Learning an Invariant Mapping},
    year={2006},
    volume={2},
    number={},
    pages={1735-1742},
    doi={10.1109/CVPR.2006.100}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->