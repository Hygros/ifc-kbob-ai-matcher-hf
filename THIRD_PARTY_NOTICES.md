# Third-Party Notices

This project uses the following third-party libraries, models, and components.

## Python Libraries

| Library | License |
|---|---|
| [sentence-transformers](https://github.com/UKPLab/sentence-transformers) | Apache-2.0 |
| [torch (PyTorch)](https://github.com/pytorch/pytorch) | BSD-3-Clause |
| [numpy](https://github.com/numpy/numpy) | BSD-3-Clause |
| [pandas](https://github.com/pandas-dev/pandas) | BSD-3-Clause |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | BSD-3-Clause |
| [faiss-cpu](https://github.com/facebookresearch/faiss) | MIT |
| [requests](https://github.com/psf/requests) | Apache-2.0 |
| [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) | MIT |
| [ifcopenshell](https://ifcopenshell.org/) | LGPL-3.0 |
| [streamlit](https://github.com/streamlit/streamlit) | Apache-2.0 |
| [plotly](https://github.com/plotly/plotly.py) | MIT |

## AI / ML Models

> **Important:** Some models have restrictive licenses.
> Check the respective model card before commercial use.

| Model | License | Notes |
|---|---|---|
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | MIT | Default bi-encoder |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | MIT | Cross-encoder option |
| [jinaai/jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) | **CC-BY-NC-4.0** | **Non-commercial only** |
| [cross-encoder/mmarco-mMiniLMv2-L12-H384-v1](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1) | Apache-2.0 | Cross-encoder option |

### License Warning

The Jina reranker (`jinaai/jina-reranker-v2-base-multilingual`) is licensed under
**CC-BY-NC-4.0** (non-commercial use only). If you intend to use this project
commercially, switch to an alternative cross-encoder (e.g., `BAAI/bge-reranker-v2-m3`).

## Frontend / Viewer

| Component | License |
|---|---|
| [ifc-lite](https://github.com/louistrue/ifc-lite) | MPL-2.0 |

Credit: The integrated dashboard viewer is based on the open-source ifc-lite project by [Louis True](https://github.com/louistrue).
