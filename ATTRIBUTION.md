# Attribution

## Google documentation (CC BY 4.0)

Sets A, B and C adapt content from Google's public documentation, which Google publishes under
the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/)
(code samples under Apache 2.0), as described in the
[Google Developers Site Policies](https://developers.google.com/site-policies).

**The content has been modified.** It was restructured as DITA 1.3 topics and MyST pages,
values were moved into keys and substitutions, and text was shortened and rewritten. Each
adapted file names its source page in its prolog (`<data name="source" href="…">`) or front
matter, and carries a licence notice. Google trademarks, logos, images and video are not used.

| Source | Used in |
|---|---|
| [Cloud TPU documentation](https://docs.cloud.google.com/tpu/docs): v5e, v5p, v6e, TPU7x, software versions, networking | `tpu/` |
| [Cloud TPU API v2 discovery document](https://github.com/googleapis/google-api-go-client/blob/main/tpu/v2/tpu-api.json) | `sources/`, `api/` (generated) |
| [Cloud NAT documentation](https://docs.cloud.google.com/nat/docs/overview): overview, Tune NAT configuration, release notes | `nat/` |
| [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4), [Gemma models overview](https://ai.google.dev/gemma/docs/core), [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3) | `gemma/evidence/` |

The full list, with the date each page was last updated and last checked, is in
[`sources/sources.yaml`](sources/sources.yaml).

Google has not engaged, sponsored or endorsed this work.

## Regulations and frameworks

The requirement topics in `gemma/requirements/` paraphrase, in plain words,
[Regulation (EU) 2024/1689 (AI Act)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj), Annexes
XI and XII, and the
[NIST AI Risk Management Framework 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf).
They are not legal advice.

## Original work

The 3D transceiver model (`media/blender/osfp.py`) and its renders (`tpu/media/`) are original,
generic designs, not any vendor's part. OSFP facts are from the
[OSFP MSA announcement of 17 March 2017](https://osfpmsa.org/press-releases/pr-20170317.html).

## Grammars

The OASIS DITA 1.3 grammars are not stored here. `tools/fetch_grammar.sh` downloads them from
the [DITA Open Toolkit](https://github.com/dita-ot/dita-ot) (Apache 2.0), which ships them as the
`org.oasis-open.dita.v1_3` plug-in.
