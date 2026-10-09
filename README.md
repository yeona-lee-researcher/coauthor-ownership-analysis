# Feeling Understood Is Not Feeling Ownership

**An exploratory reanalysis of the CoAuthor dataset: surveys, keystroke logs, and a validated microsimulation**

Trial project, Option 2 (examine the code and data). Dataset: [CoAuthor](https://coauthor.stanford.edu/) (Lee, Liang & Yang, CHI 2022).
All findings are observational associations.

**Start here**

0. The essay below: the personal motivation for this project, drawing on three papers on creativity.
1. [`paper/main.pdf`](paper/main.pdf): the full 8-page write-up (methods, every table, validation, limitations).
2. The five bullets and key results below.
3. [`qualitative_codes_en.csv`](qualitative_codes_en.csv): the thematic analysis. It covers 23 contrastively sampled comments, each with codes, one of five themes, an English paraphrase, and an interpretive limit.

---

## Essay: Giving Shape to the Trajectory of a Life — Where Creativity Begins

*The essay below states the personal motivation behind this analysis, drawing on three papers on creativity.*

### When Experience Becomes a Question

I believe that one starting point of creativity lies in the unique trajectory of a person's life. Even when we witness the same scene or acquire the same knowledge, what stays with us and what we ultimately come to question are different. What we have loved, what we have lost, and what we wish to protect direct our attention toward particular things. In this way, experience becomes interest, interest becomes a question, and a question leads us to imagine something that does not yet exist.

This idea resonates with what Kaufman and Beghetto (2009) describe as *mini-c creativity*: personally novel and meaningful interpretations of experience. From this perspective, creativity can begin in everyday life. It emerges when something others might pass by becomes a problem I want to solve, or when I discover a curiosity of my own in an otherwise familiar landscape.

I would like to call the attitude underlying this starting point *authenticity*. By authenticity, I do not mean repeatedly expressing some fixed version of myself. Rather, I mean being honest with the person I am becoming through experience and learning, and consciously choosing what matters to me. It goes beyond pursuing what simply "feels like me." It means asking why I make certain choices and how I am willing to take responsibility for them.

Authenticity does not guarantee creativity, but it can serve as a compass, guiding which possibilities we explore and what we ultimately recognize as valuable.

### Loving What We Do and Learning Along the Way

These choices can become clearer when we are deeply immersed in something we love. There are moments when our concern about how others perceive us fades, and our attention becomes fully absorbed in the problem and the possibilities before us.

Yet authenticity does not always mean feeling happy or finding things easy. It can also reveal itself in the willingness to stay with something we do not understand, to revise our own thinking, and to return to uncomfortable questions.

Amabile's (2012) theory of creativity likewise emphasizes not only intrinsic motivation, but also domain-relevant expertise, creativity-relevant processes, and a supportive environment. Passion gives us a reason to keep exploring, while learning allows that passion to take concrete form.

This is why learning remains important even in the age of AI. As we acquire knowledge, we learn to make finer distinctions, ask more precise questions, and examine our intuitions against evidence.

AI opens up new possibilities within this process of learning and experimentation. It can help us understand unfamiliar concepts, compare different ways of expressing an idea, and test ideas that might otherwise have been difficult to implement.

But as the distance between imagination and implementation grows shorter, we must distinguish between obtaining a result and truly understanding it. Reflecting on what we understand and what remains unclear becomes an essential part of learning with AI.

Still, the fact that we can turn imagination into reality more easily does not necessarily mean that we can create something more distinctly our own than previous generations could.

In an experiment on short-story writing, Doshi and Hauser (2024) found that access to AI-generated ideas improved creativity ratings while also increasing similarities among the stories.

This finding raises an important question: **When we think and create alongside AI, what should remain our own?**

What question did I begin with? Of the possibilities suggested to me, which did I accept, which did I change, and why did I ultimately choose this result as my own work?

Authenticity becomes visible in what we create through these acts of judgment. Along the way, remaining rooted in our own experiences and welcoming new perspectives that take us beyond our familiar selves need not be contradictory. They can happen together.

### So, What Does This Mean?

**Be grounded. Be you.**

Stay rooted in the life you are living, engage deeply with what you do, and remain open to unfamiliar experiences that draw you in and allow them to change you.

The kind of creativity I hope to see in the age of AI is one in which this way of living meets technology and reaches beyond what was previously possible.

With AI, I want to turn questions I have carried with me for a long time into things I can begin exploring and creating today. And through that process, I hope to discover anew what it is that I love.

**We give shape to the trajectories of our lives, and what we create, in turn, reshapes the direction of the lives we have yet to live.**

### From the essay to the analysis

The essay's question — *what should remain our own when we create alongside AI?* — is what the analysis below operationalizes. In CoAuthor, "remaining our own" can be observed only partly, through ownership ratings, how much a writer typed, and which suggestions they accepted or rejected. Authenticity, motivation, and well-being themselves were not measured.

**Essay references**

- J. C. Kaufman, R. A. Beghetto. Beyond big and little: The four C model of creativity. *Review of General Psychology* 13(1):1–12, 2009. https://doi.org/10.1037/a0013688
- T. M. Amabile. Componential theory of creativity. Harvard Business School Working Paper 12-096, 2012.
- A. R. Doshi, O. P. Hauser. Generative AI enhances individual creativity but reduces the collective diversity of novel content. *Science Advances* 10(28):eadn5290, 2024. https://doi.org/10.1126/sciadv.adn5290

---

## Describe your analysis (five bullets)

- **(1) Motivation.** I examined whether feeling understood by an AI writing assistant goes together with feeling that the text is one's own. The analysis separates stable differences between writers from variation across the same writer's sessions.
- **(2) Hypothesis.** In sessions where a writer felt more understood than usual, ownership would be higher, after accounting for the human share of text, prompt, and model setting.
- **(3) Approach.** I linked CoAuthor metadata and surveys (1,407 sessions, 61 writers) and fit within/between-writer ordinal GEEs. I then replayed all 1,447 keystroke logs with per-character provenance, which matched the metadata in 99.9% of sessions. From these logs I built a writer-level microsimulation of writing, pausing, and requests, validated on unseen writers and on later sessions. I also preliminarily coded 23 contrastive comments.
- **(4) Quantitative and qualitative results.**
  - The hypothesis was not supported (OR = 0.85, 95% CI [0.66, 1.09]).
  - Feeling understood instead tracked ideation help (OR = 3.40 [2.76, 4.18]).
  - In the logs, it also tracked system availability: more unanswered requests went with lower understanding (OR = 0.77 per 10 pp [0.69, 0.86]).
  - Writer-specific simulation parameters predicted 35 of 39 writers' later sessions better than a population model.
  - Comments showed useful help with low ownership ("closer to an editor than a writer").
- **(5) Findings.** Ideation help, availability, and ownership should be evaluated separately. Writers show recurring interaction styles that still vary across sessions; these are behavioral regularities, not personality. Whether a writer's desired and experienced roles match is a promising next question. All results are exploratory and observational.

---

## Key results

### Survey models (within-writer, ordinal GEE, writer-clustered 95% CI)

| Association | Odds ratio [95% CI] | Verdict |
|---|---|---|
| Understanding → ownership (**H1, primary**) | 0.85 [0.66, 1.09] | not supported |
| Understanding → ideation help (H2) | 3.40 [2.76, 4.18] | supported |
| Understanding × ideation → ownership (H3) | 0.94 [0.88, 1.01] | not supported |
| Human share +10 pp → ownership | 1.33 [1.13, 1.56] | positive |
| Between-writer understanding → ownership | 2.36 [1.57, 3.55] | weakens to 1.37 [0.98, 1.93] with equal writer weights |

- None of the ten sensitivity analyses produced a positive within-writer understanding–ownership association.
- The linear writer fixed-effects estimate was −0.09 points [−0.23, 0.04]; the writer bootstrap gave [−0.21, 0.03].

### Interaction logs

| Result | Value |
|---|---|
| Requests never answered | 6.8% of 18,089 (4.1% creative, 11.8% argumentative) |
| Unanswered requests +10 pp → understanding (within writer) | OR 0.77 [0.69, 0.86] |
| More suggestions shown (+1) → understanding | OR 1.35 [1.10, 1.66] |
| Revising AI-inserted text +10 pp → ownership | OR 1.00 [0.84, 1.18] (none) |
| Idle time before a request | median 0.41 s; only 2.1% after ≥ 10 s of inactivity |
| Accepted suggestion followed by more human writing | 86–87% of the time |

### Microsimulation

| Check | Result |
|---|---|
| **A. Unseen writers**: log-likelihood per event, frequency-only → first-order → + session variation | −1.27 → −0.80 → −0.75 |
| **B. Later sessions**: writer-specific vs. population model | +0.068 nats/event [0.041, 0.106]; better for 35 of 39 writers |
| B. 90% interval coverage (target .90): Q episodes / accepted / human share / duration | .58 / .58 / .54 / .89 → .81 / .81 / .77 / .93 |
| B. Error in predicted human share | 15.6 → 10.7 pp |
| **C. Writer clustering** (ICC, observed → simulated, in-sample) | creative human share .56 → .54; argumentative .70 → .57; duration .6 → .06–.15 |
| **D. Scenario** (model-implied, not causal): never-answered requests answered | +0.53 accepted suggestions per session, −1.3 pp human share |

### How to read these results

- **A. The order of actions carries information.**
  - The baseline is not a random model. It knows how often each action occurs, but not what follows what. Adding the previous action improves prediction sharply.
  - The session-variation model updates on transitions already seen in the same session. Its gain means that patterns emerging during a session are informative, not that a style is known in advance.
- **B. A writer's past collaboration helps anticipate their future collaboration.**
  - This is the most direct answer to whether individuals bring a recurring "internal component" to their interaction with AI.
  - +0.068 nats/event is an improvement in the log-probability given to what actually happened, not an accuracy percentage.
  - Coverage measures how realistically the model anticipates the range of behavior. It remains below .90, so much session-to-session variation is unexplained.
- **C. Writer differences account for much of the between-session variation.**
  - This is an in-sample check, not held-out validation.
  - Overall session length is reproduced well. What is not reproduced is which writers consistently write long or short sessions, which suggests that stopping depends on different information than requesting and accepting.
  - An ICC of .84 does not mean 84% of behavior is "personality". Skill, task choice, strategy, and habit all contribute.
- **D. The scenario quantifies the scale of availability failures under the model.**
  - A lower human share means more AI-inserted characters, not less human direction or creativity.

---

## Data

| Source | Content | Access |
|---|---|---|
| Metadata & surveys | Four sheets: `Metadata (creative)`, `Metadata (argumentative)`, `Survey (creative)`, `Survery (argumentative)` (the last spelling is original) | [Google Sheet](https://docs.google.com/spreadsheets/d/1O3EXJm52TQHfFSbzVGZmNIzzdu5ow6IjnOBrGTUY02o/edit), downloaded as XLSX by `download_data.py` |
| Interaction logs | 1,447 `.jsonl` files (`coauthor-v1.0/`), one per session; every keystroke, cursor, and suggestion event with timestamps and Quill text deltas | "Download writing sessions" on [coauthor.stanford.edu](https://coauthor.stanford.edu/) ([Google Drive](https://drive.google.com/file/d/1C9FCCsyY-5I7mcBHi-__R7lxHkGX_-9Q/view)) |

**Units and sample.** Each row is a writing session, and the same writer completed up to 89 sessions.

| Step | n |
|---|---|
| Metadata sessions | 1,445 (creative 830, argumentative 615) |
| Survey rows | 1,458 (3 excess duplicates: latest kept; 11 unmatched: not imputed) |
| Linked sessions | 1,444 (worker IDs agree for all) |
| Zero-request sessions (observed non-use, not missing data) | 37 excluded |
| **Analysis sample** | **1,407 sessions, 61 writer IDs** |

**Variables.**

- **Ratings (1–7):** perceived understanding ("The system understood what I was trying to write"), ideation help ("The suggestions helped me come up with new ideas"), and ownership ("I feel like the story/essay is mine").
- **Human share:** `written_by_human`. The replay shows it is the human share of *inserted* characters, not of the final text.
- **Design factors:** prompt (20 levels) and the genre-specific decoding setting (creative T .75 / FP 1 vs. .3 / 0; argumentative T .9 vs. .2, FP .5).
- **Session duration:** not treated as time pressure, because the CoAuthor timer showed a minimum writing time, not a deadline.

**Checked against the CoAuthor paper.**

- **Writer count:** the paper reports 63 writers (58 creative, 49 argumentative), whereas the public metadata contain 61 unique IDs (57, 47).
- **Ownership scale:** Section 5.2.2 describes ownership as a 5-point scale, whereas responses range 1–7 and Appendix C lists the other items as 7-point.
- **Consistency with the paper:** our correlation of ownership with human share (Spearman .28) agrees with the paper's r = 0.3. Our null link between revising AI text and ownership agrees with its r = 0.1 for edits.

**Not included.** Raw data and participant comments are re-downloaded from the public source. Generated `data/` and `results/` folders are git-ignored because they contain participant comments. Use of the data follows the original distribution's terms; this repository adds no license to the data.

---

## Modules

```
run_pipeline.py --input <xlsx> [--logs <coauthor-v1.0>] --out results
 ├─ analyze.py           survey linkage and cleaning → ordinal GEE, sensitivity analyses, writer bootstrap, contrastive sampling
 ├─ join_qualitative.py  attach the 23 preliminary codes only if session ID, genre, ratings, and comment hash all match
 ├─ make_tables.py       model outputs → results/tables.md
 ├─ process_logs.py      log replay with per-character provenance; episodes W / P / QA / QR / QN   (with --logs)
 ├─ process_models.py    E0 replay validation; E1–E4 log-linked models                           (with --logs)
 ├─ simulate.py          semi-Markov microsimulation; validations A–B, ICC check C, scenario D   (with --logs)
 └─ make_figures.py      simulation figure                                                       (with --logs)
```

| File | Role | Main outputs |
|---|---|---|
| `stats_core.py` | Shared estimators: cluster-robust logistic GEE, ordinal GEE (stacked cumulative logits, writer sandwich, G/(G−1) correction, t(G−1) intervals), cluster OLS | — |
| `analyze.py` | Survey models, sensitivity analyses, numerical checks (analytic vs. finite-difference gradient, intercept-only probabilities, Frisch–Waugh–Lovell) | `model_results.csv`, `audit.json`, `descriptives.csv` |
| `process_logs.py` | Replays every Quill delta, labeling each character as prompt, human, or AI. Segments sessions into writing bursts (W), pauses ≥ 10 s (P), and requests accepted (QA), rejected (QR), or with no suggestions shown (QN). Handles late displays and reopened lists | `process/session_process.csv`, `process/episodes.csv` |
| `process_models.py` | E1 availability → understanding; E2 AI revision → ownership; E3 pauses and requests; E4 writing after each request outcome | `process/process_models.csv`, `process/process_audit.json` |
| `simulate.py` | First-order transitions shrunk toward the genre (κ); session-level Dirichlet variation (α); writer stopping hazard (κ_h); episode contents resampled jointly. Hyperparameters are tuned on training data only | `simulation/simulation_report.json`, transition tables |
| `make_figures.py` | Observed vs. simulated human share; predictive-interval coverage | `figures/fig_simulation.pdf` |
| `verify_results.py` | Compares a rerun with `reference_results/`; reports quasi-separated nuisance terms instead of failing | — |
| `download_data.py` | Downloads the metadata XLSX and rejects login pages saved as XLSX | `data/raw/coauthor_metadata.xlsx` |
| `qualitative_codes.tsv`, `qualitative_manifest.csv` | Original preliminary codes and the identity/hash manifest used to attach them | — |
| `qualitative_codes_en.csv` | English codebook: codes, five themes, paraphrases, interpretive limits | — |
| `tests/` | 6 data-guard tests (reassigned cases, edited comments, bad downloads) and 3 replay tests (provenance, episode types, late displays) | — |
| `reference_results/` | Frozen aggregate outputs reported in the paper, including `process/` and `simulation/` | — |

---

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python download_data.py                              # metadata XLSX -> data/raw/
# logs: download "writing sessions" from coauthor.stanford.edu and unzip -> coauthor-v1.0/*.jsonl
python run_pipeline.py --input data/raw/coauthor_metadata.xlsx --logs path/to/coauthor-v1.0 --out results
python verify_results.py --out results               # compare with reference_results/
python -m unittest discover -s tests                 # 9 tests
```

- The full pipeline runs in under a minute with fixed seed 20261009 (500 writer-bootstrap resamples, 100 simulated replicates per session).
- If the download fails, open the Google Sheet, choose *File → Download → Microsoft Excel (.xlsx)*, and save the file as `data/raw/coauthor_metadata.xlsx`.
- Without `--logs`, only the survey and qualitative steps run.

**Verified reproduction.** All results reproduce across three software stacks: Python 3.12 / SciPy 1.17, 3.14 / 1.18, and a fresh clone on 3.11 with a freshly downloaded workbook.

- All 547 survey-model parameters match to 1e-5.
- Log-model estimates match to 2e-8.
- The simulation report is identical byte for byte.

Three prompt coefficients in the `O > 3` threshold model are not identified (quasi-complete separation, |β| ≈ 29). The verifier reports them instead of comparing them.

**Safeguards.**

- **Different workbook bytes:** a re-exported Google Sheet can differ in bytes (reference SHA-256 `bb850549…47c4`). Compare the cohort and model outputs, not only the file hash.
- **Qualitative codes:** codes are attached to a case only when session ID, genre, ratings, and comment hash all match. If the source changes, run with `--skip-pilot-codes`; this removes stale qualitative output rather than forcing old codes onto new data. A hash match does not replace human review of the interpretations.
- **Statistical implementation:** the ordinal GEE was implemented in NumPy/SciPy, not statsmodels. A formal proportional-odds test and an independent reimplementation in other statistical software remain to be done.

---

## Interpreting the results responsibly

- **H1:** the primary hypothesis was not supported. Negative estimates in some sensitivity analyses are not promoted to a new hypothesis.
- **Ideation help:** the understanding–ideation association involves self-reported ideation help, not externally rated creativity or a causal effect.
- **Post hoc analyses:** the log analyses (E1–E4) and the simulation were specified after the survey results. The survey hypotheses were set before the first model run but were not preregistered.
- **Behavior, not traits:** individual "styles" are behavioral regularities in this task, not measures of personality, intrinsic motivation, authenticity, or well-being.
- **Not measured:** time pressure, authenticity, and mental health.
- **Qualitative codes:** the 23 codes are preliminary and AI-assisted; human review is pending.
- **Generalization:** the data come from paid crowdworkers using GPT-3 in 2021.

**AI assistance.** AI assistance was used for coding, analysis, and writing. All reported results were reproduced and verified, including from a fresh clone.

---

## References

1. M. Lee, P. Liang, Q. Yang. CoAuthor: Designing a human–AI collaborative writing dataset for exploring language model capabilities. *CHI 2022*. https://doi.org/10.1145/3491102.3502030
2. F. Draxler et al. The AI ghostwriter effect. *ACM TOCHI* 31(2), Article 25, 2024. https://doi.org/10.1145/3637875
3. P. J. Curran, D. J. Bauer. The disaggregation of within-person and between-person effects in longitudinal models of change. *Annual Review of Psychology* 62:583–619, 2011.
4. R. M. Ryan, E. L. Deci. Self-determination theory and the facilitation of intrinsic motivation, social development, and well-being. *American Psychologist* 55(1):68–78, 2000.
5. V. Braun, V. Clarke. Can I use TA? Should I use TA? Should I not use TA? *Counselling and Psychotherapy Research* 21(1):37–47, 2021.
