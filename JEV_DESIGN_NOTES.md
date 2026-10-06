# Jev design notes: to implement later

Compiled from TypeSafe's docs as the owner and Claude read them together. Nothing here is built yet.
The owner has decided all of it goes into the coach's structure; this file is the running list.

## From "Intent routing"

1. Route by intent to three kinds of handler:
   - plain code, no LLM: "stop", "explain more", "am I on track";
   - a prepared answer from the library for common questions it covers well;
   - Claude with a small, focused brief per topic (jungle pathing, objectives, plan changes), not one big prompt.
2. Ask a second judgment in the same request as the intent: a score for "standard question versus unusual situation". Use it, alongside the fit rating, to choose between a prepared answer and Claude.
3. When intent confidence is low, do not guess. Ask the player a short clarifying question.
4. Check the confidence of the score as well. An uncertain rating means "send to Claude", not "medium".

## From "Confidence-gated routing"

5. One floor for "did I understand you" on every sentence. Below it, do not act on the guess: clarify or hand to Claude.
6. Different cut-offs per action, set by what a wrong guess costs:
   - low cost (speaking a prepared answer, which the player can reject with "not that"): a lower cut-off is acceptable;
   - high cost (locking or changing the plan for the match, dropping a plan, saving a champion note to file): a high cut-off.
7. In the middle band for high-cost actions, confirm in a few words before acting ("Locking six on crab?").
8. Always include an "other" intent, and send "other" to the fallback (Claude) even when confidence is high.
9. The numbers in the docs (0.5, 0.6, 0.85) are examples. Set ours from tests on the owner's real sentences. The single 0.75 cut-off from the first test should become per-intent cut-offs.

## From "Guardrails for LLMs"

14. Guard both sides of Claude with one Jev request each: the player's transcribed sentence on the way in, Claude's line on the way out. Rules written in Claude's prompt are not enough on their own.
15. Use a battery, not one question: one noul per hazard plus one severity score, all in the same request.
    - Output hazards for the coach: states something unseen as fact; invents a number; contradicts a verified game rule; gives a single order with no alternative; does not answer what was said; repeats a prepared answer when options were asked.
    - Input hazards: not a coaching question; text that tries to instruct the assistant; (later) the player sounds tilted.
    - Severity score: how much it costs the player if the line is wrong, from harmless to game-losing.
16. Two cut-offs per hazard, review and action, and each hazard maps to its own action:
    - pass: speak it;
    - review: have Claude rewrite once, or fall back to a prepared answer;
    - block: do not speak it; use the fallback.
    A high severity turns a review into a block.
17. Keep the cut-offs in code as named policies (for example strict and relaxed). The same Jev result can be routed differently without asking Jev again.
18. Set the cut-offs from labelled examples of the coach's own lines, not from the doc's numbers.
19. (Later, optional) a "support" route: if the player sounds tilted, a calm reset line instead of a tactical call.

## From "Re-ranking"

20. Keep the two-step search for prepared answers: a fast search cuts thousands of entries to a shortlist, then Jev rates each shortlisted entry and the coach sorts by that rating.
21. The rating step can only reorder what the shortlist contains. Improve the shortlist (proper keyword ranking such as BM25, a longer list of about 30, possibly meaning-based search) and measure separately how often the right entry makes the shortlist.
22. Ask several questions about each candidate in one call, not one: answers what was asked; fits this role, champion and game time; presupposes something the coach cannot see. Combine them in code.
23. Sharpen the yes/no wording: "yes" means it gives the specific thing asked for; "no" means it is merely on a similar topic.
24. Even re-ranked, the top pick is often not the right one (the doc's own example went from 5% to 18% in first place). Keep the confidence gate and the Claude fallback, and pass the top few candidates to Claude as material.

## From "Skill suggestion"

26. Let Jev do the shortlisting by meaning, in two requests:
    - Request 1: one choice question over every eligible prepared answer, one short line each, so its probabilities are the ranking. A choice holds at most 255 options, so filter by intent, role, champion and phase first, and split into chunks if still too many.
    - Request 2: only the top three, now with their full detail, re-checked.
    This replaces the crude word-overlap shortlist (item 21).
27. Use the two question types for different jobs: a choice among the top three decides WHICH answer; a separate yes/no per candidate decides WHETHER any of them should be spoken. Either request may come back with "nothing fits".
28. Add gate questions to request 1 about what kind of response the player wants, not about the subject: for example "is the player stating a plan or asking a question", "does this need a judgment about this specific game", and one worded the opposite way ("would a standard answer fully satisfy this"). Their average decides prepared answer versus Claude.
29. When a prepared answer is passed to Claude, pass it as a hint that can be ignored ("ignore this if it does not fit what the player said"). When nothing fits, say so explicitly rather than passing nothing.
30. A confident wrong suggestion is more persuasive than none. The doc's suggestion fixed 37 cases and broke 7. This matches our test, where Claude repeated a prepared answer word for word. Keep the hint weak and count how often it hurts.
31. Build the test set with "nothing fits" cases on purpose, including near-misses where the library has something close but wrong. Report two error rates: wrong answer picked, and an answer picked when none should be.

## Owner's note: marking coach lines good or bad

25. The cut-offs in items 9 and 18 need labelled examples of real coach lines. Decide with the owner how to make marking easy before building it. Ideas so far, none decided: saying "good" or "bad" by voice right after a line; a review at the end of the game. Discuss this specifically when implementation starts.

## From "Introduction"

32. Split the old ranking question. Today one Jev question asks it to rank plays while weighing safety, gold, tempo, structures, vision and objectives at once. Ask each factor as its own question per candidate and combine the results in code.
33. Make the team's style a number in code, not prompt text. "Aggressive / balanced / cautious" (the /approach command) becomes weights on the separate scores, for example risk counting for less when aggressive.
34. Use the "gut-check" test to divide the work: facts the feed gives are computed in code; a judgment a knowledgeable person could make in a few seconds goes to Jev; anything that needs reasoning across several factors, or wording, goes to Claude.
35. Adding questions to a request barely changes its time and they do not interfere with each other, so put every independent judgment about the same sentence and game state into one request.

## From "Quick start"

37. Use the Playground (console.typesafe.ai/playground) to try question wording by hand before putting it in code: paste a real player sentence as the state, add the questions, read the answers. The owner and Austin can do this themselves with no code.
38. Consider replacing the coach's hand-written web calls to Jev with TypeSafe's Python SDK (typesafe-sdk, needs Python 3.10 or newer), which handles retries and has an async client that suits the bot. Check it installs on the bot's Python 3.14 first.
39. Every Jev response reports token usage. Log it per question so the real cost of the coach is known.

## From "Jev with coding agents"

40. Do not ask Claude to return a structured reply. Claude returns only the plain spoken sentence; every structured judgment about it (does it answer the question, does it leave a choice, does it claim something unseen) comes from Jev.

## From "Example use cases"

41. Pull facts out of what the player says. When the player reports things the feed cannot see ("our top is pushed in", "their jungler just showed bot", "crab is about to spawn"), have Jev extract them into known fields and keep them as "reported by the player", separate from observed facts, with a time stamp so they expire.
42. Route between Claude models. Have Jev estimate how hard the question is; send easy ones to the small fast model and only hard ones to a bigger one.
43. Gate unprompted speech. Jev is fast enough to run a yes/no every few seconds on "has something changed that is worth saying?". This could bring back spoken updates without the constant chatter that got them switched off.
44. Log every check's result and probability in a structured form, so a bad answer can be traced to the step that caused it.
45. (Later) Use Jev's judgments as features and the owner's good/bad marks and game outcomes as ground truth, to learn which signals predict a good call. Depends on item 25.

## From "System One"

46. Jev's probabilities are right on average across many answers, not for each one. A 0.84 can still be wrong. Judge cut-offs by error rates over a batch of labelled examples, and keep recovery from a wrong answer cheap ("not that").
47. Put the rules in the state. Like the doc's refund example, each request should carry the player's sentence, the observed facts, the player-reported facts, and the rule or lesson being judged, so Jev can answer "does this lesson's condition hold here?". Hard timers and arithmetic stay as checks in code.
48. Jev reads text only: no images, audio or video. It cannot read the minimap or the screen. The minimap reader stays separate code, and its output goes into the state as text.

## From "State"

49. Keep Jev's state as a named object for Coach, with the player's exact question, observed game facts, time-stamped player reports, current plan, and the specific lesson or candidate being judged in distinct fields. Preserve the source of each fact so a player report or a static champion description is not treated as a live observation. This expands item 47.
50. Build the state around the decision at hand: include related facts that need comparing, but avoid dumping unrelated history or whole playbooks into every request. Keep one clear snapshot for all questions in that request.
51. Ask independent judgments about that same snapshot together where useful, mixing choice, score, and noul questions. Questions define what Jev should decide; the state carries the evidence. This elaborates item 35.
52. Coach already sends a structured `ranking_state` object to Jev, but its live ranker currently asks one broad `next_play` choice question. When implementing items 32 and 35, reshape that request into smaller judgments over the shared state and verify each field's source and freshness.

## From "Primitives (Questions)"

53. Match the question type to the answer Coach needs: Choice for one of named routes or candidate plays (with an `other`/`none` option when needed), Score for an ordered degree such as risk or opportunity strength, and Noul for a specific yes/no check such as whether a line assumes unseen information.
54. Define each judgment in its `instructions`, not just its code ID; IDs identify response fields but are not sent to the model. Give Choice options and Score levels explicit criteria. In a structured state, point a question to the exact field it should judge, for example `player_question` or `candidate.play`.
55. Read Noul as the probability of yes, not as a graded amount: 0.5 means uncertainty between yes and no, not medium risk. Use a Score with defined levels when Coach needs the degree of risk. Choice and Score also return option/level probabilities and confidence; use the full distribution and calibrated thresholds for routing.
56. Ask independent questions over the same state in one request, including cheap speculative questions that code may ignore. Split broad play selection into focused judgments (safety, fit, tempo, payoff, unseen assumptions) and combine them with named weights in code. This makes items 32 and 35 concrete.
57. Make a second Jev request only when the first answer changes the evidence or available options: for example, shortlist candidate answers, then retrieve their full text and judge the finalists. If every question can use the original state, send them together and let code select which answers matter.

## From "Choice"

58. Treat the selected Choice as the highest-probability option, not proof it is safe to use. Read its full probability distribution and confidence: close alternatives may both be relevant, and a low-confidence choice should trigger clarification or Claude rather than a forced prepared answer.
59. Include all eligible, clearly named options in a Choice when feasible (the documented limit is 255), with an `other` or `none fits` route for incomplete lists. Write descriptions that distinguish neighbors; if Coach repeatedly confuses similar routes, give each structured `what`, `not_for`, and example guidance.
60. For a multi-part player request, ask several Choice questions over the same state (intent, requested response, topic, applicable plan) and use only the answers relevant to the route. Do not assume the highest-probability label captures every part of what the player asked; preserve meaningful secondary probabilities where the code has a use for them.
61. Coach's current `jev_rank` uses the Choice probability map to rank candidate plays but discards `choice` and `confidence`, and offers no explicit `none fits` candidate. Review that behavior when adding the confidence and fallback gates from items 5-9 and 27-31; set thresholds from real labelled Coach cases, not the documentation's support-ticket examples.

## From "Noul"

62. Write one precise, positively oriented yes/no proposition per Noul. Split compound checks such as "does this answer invent a location and a timer" into separate questions, and combine their results in code. Use optional true/false criteria only when the boundary needs explanation.
63. Treat a Noul value as probability of yes, with no separate confidence field. Values near 0.5 mean uncertainty, not a moderate amount of the property. Route an uncertain middle band to clarification, Claude, or a safe fallback; choose per-check thresholds from labelled Coach examples and the cost of each error.
64. Run separate Nouls over a shared state for input and output checks: whether the player asks for options, whether a prepared answer actually answers the question, whether a Coach line claims unseen location, whether it invents a number, and whether it contradicts verified facts. This makes the hazard battery in items 14-18 concrete.
65. Noul values can rank candidates without immediately becoming yes/no decisions. For the answer library, ask one precise fit question per candidate and sort by its probability, then use a separate suitability gate so the best of several bad entries is not spoken.
66. When checking many candidates or fields, keep shared evidence in state and put each candidate or field in a structured question instruction. Use stable question IDs to associate each returned value with its candidate; the ID alone does not tell Jev what to judge.

## From "Advanced: structure"

67. Jev accepts JSON structure inside `instructions`, Choice option descriptions, Score level descriptions, and Noul `criteria.true`/`criteria.false`. Start with short strings; use named objects or arrays when a judgment needs several labelled parts or code already has structured data.
68. For close Coach intents or prepared answers, define each Choice option with `what`, `not_for`, and a few real player examples. For a Score, give each level a summary and observable signals. For a subtle Noul, define true and false with contrasting examples. Test whether that extra structure improves mistakes before expanding every question.
69. Keep a question's main instruction and its supporting data together in a structured `instructions` object when needed; reference the relevant state fields by name. For candidate checks, share the match snapshot in state and put each candidate's compact facts in its own question instructions.
70. Audit `coach.py`'s `jev_rank` request: `role_rule` is currently a sibling of `type`, `instructions`, and `criteria`, while this page documents structure inside `instructions` or criteria values. Check the API response or SDK schema to see whether `role_rule` is honored; move its important guidance into documented `instructions` structure during implementation if it is not. Do not assume Jev has seen that rule merely because the HTTP request succeeded.

## From "Confidence"

71. Choice and Score confidence are deterministic summaries of the returned option/level probabilities, not independent evidence that the selected answer is factually correct. A confident wrong choice remains possible; retain `none fits`, observed-fact checks, and labelled-case calibration from items 31 and 46.
72. Choice confidence depends on the number of options and only the largest probability, so inspect the top probability and runner-up as well for Coach's top-two play presentation. Compare thresholds within a stable question/option set or calibrate separately as the candidate count changes.
73. Score confidence uses the order and distance between levels: uncertainty between adjacent risk levels differs from uncertainty between safe and dangerous extremes. Define ordered levels carefully and preserve the level distribution when a spread across extremes would change the decision.
74. Noul has no confidence field; its yes probability itself is the signal. If shared gating code requires a confidence-like value, compute `abs(2*p - 1)`, while keeping the original probability to know whether the answer leaned yes or no.
75. Use three-way routing where appropriate (act, verify/clarify, fallback) with thresholds set per action and its error cost. In Coach, speaking a reversible suggestion, changing a persistent plan, and saving a player note need different gates. Start with conservative values and tune them on labelled real questions rather than adopting the banking example's 0.5 or 0.9.

## From "AI primer"

76. TypeSafe positions Jev as a narrow decision model trained for structured outputs and calibrated probabilities, rather than a text-generating conversational model. Keep Jev for bounded judgments that Coach's code can inspect, and use Claude for reasoning and spoken wording. This reinforces items 34 and 40.
77. Calibration describes batches, not individual certainty: among many outcomes assigned 0.8, about 80% should be positive if the model is calibrated on Coach's task. Measure this on labelled real Coach questions before trusting probability-based routing; a single high value can still be wrong. This extends item 46.
78. The primer's RLHF, RLVR, and RLCD comparison is TypeSafe's explanation of its training approach, not evidence that Jev is accurate on League. Do not treat its machine-native positioning or training claims as a substitute for Coach-specific evaluations.

## From "Patterns" and "Speculative fan-out"

79. The Patterns page is an index of four patterns; intent routing and confidence-gated routing were covered earlier, and composite scoring is already planned in items 32-33 and 56. Track speculative fan-out as the new detailed pattern in this batch.
80. In one Jev request, ask all independent questions that might be needed for the same state, even branch-specific ones, then let code ignore irrelevant answers. For Coach, a shared player-question snapshot can ask intent, desire for options, plan-change request, and answer-fit checks together when each can be judged from that snapshot. This elaborates items 35, 51, and 56.
81. Fan-out avoids a second network round trip only when every question has enough evidence in the first state. If a later judgment needs newly fetched candidate text or a state assembled from an earlier answer, keep the second request (item 57). Additional questions still cost tokens, so log actual latency and token usage as in item 39.

## From "Composite scoring"

82. For each candidate play, ask focused Score questions about independently judged dimensions such as safety, immediacy, role fit, and longer-term payoff, with clear ordered levels; normalize the returned scores to a common 0-1 scale before combining them. This is the concrete procedure behind items 32 and 56.
83. Keep weights in Coach code, keyed by the player's `/approach` style or the type of request. The same Jev dimension scores can be recombined for aggressive, balanced, or cautious rankings without changing the questions or calling Jev again. Inspect component scores when a ranking is surprising and tune weights against labelled examples.
84. Do not let a weighted average override a hard impossibility or unsupported fact: use deterministic eligibility checks and the planned unseen-fact/safety gates before ranking. A high payoff score cannot make an impossible or unobserved setup valid.

## From "Cookbooks" index

85. This page is a navigation index, not a worked recipe. Already reviewed in depth: Re-ranking, Skill suggestion, and Guardrails for LLMs. Do not redo those when working down the cookbook list; review newly pasted recipes on their own evidence.
86. Priority recipes to inspect for Coach's current failures: Self-consistency (stability of Jev judgments), Parallel questions (voice latency and token cost), Line-by-line search and Classifying RAG passages (answer-library retrieval and fit, after the library work resumes), Double-checking citations (whether a sourced lesson actually supports a spoken claim), and Classification using confidence (fall back to a broader response when a specific route is uncertain).
87. Potential later recipes: SDE cascade and pre-parsed/date extraction for player-reported facts, Function calling for safe closed-set commands, Hierarchical classification for a large play taxonomy, and Autoresearch feature discovery only after enough labelled Coach outcomes exist. A cookbook's reported results on its own dataset do not establish performance on League coaching.

## From "Self-consistency: nouls"

88. In offline evaluation, repeat the same state and Noul battery across runs and record each raw probability, the resolved Jev model version, latency, and token usage. Measure per-question spread and, more importantly, whether repeated values cross Coach's proposed action threshold. Do not add 15 calls to a live voice turn.
89. Give uncertain Noul values an explicit middle route instead of forcing a yes/no at 0.5. The cookbook's inclusive 0.30-0.70 band is illustrative, not a Coach threshold; tune each check's band against labelled examples and the cost of false action versus fallback.
90. Test both obvious and borderline Coach cases: player intent, answer-library fit, unsupported location or timer claims, and proposed plan changes. Stability is not correctness; compare repeated answers with human labels as well as with one another, and preserve probabilities in logs so decisions can be audited.
91. The cookbook varies an irrelevant `uid` on each run; its authors say this cannot distinguish sensitivity to that field from variation on identical inputs. For Coach, test identical requests and harmlessly perturbed requests separately, and make caches include a fingerprint of the state and question wording to avoid stale evaluation results.

## From "Classification using confidence"

92. When a narrow Choice route is uncertain and a reliable hierarchy exists, return the parent category without another Jev call. For Coach, a doubtful specific question topic might fall back to a broad coaching topic or a general Claude route; do not infer a parent from an invalid or out-of-scope winner.
93. The cookbook's 0.9 cutoff and 27/30 versus 12/30 narrow-label results come from 60 prefiltered SEC filings under `jev-1.12`, not Coach. Evaluate both narrow accuracy and parent-category accuracy on labelled player questions, and track how often Coach must fall back to broad replies.
94. Important documentation inconsistency: this cookbook says Choice `confidence` distinguishes a 0.45 winner with a 0.44 runner-up from a 0.45 winner whose remainder is diffuse. The separate Confidence page's stated Choice formula uses only top probability and option count, so those cases have the same confidence if the number of options is fixed. Inspect `probabilities` directly (top-two gap/ratio) when runner-up separation matters.

## From "Self-consistency: choices"

95. Offline, rerun the same eight-style Choice rubric on borderline Coach utterances and log full probability vectors as well as selected labels; a small probability shift can flip a top label even if values are otherwise stable. Test exact repeats separately from requests with a changing irrelevant uid.
96. Add an explicit uncertain route when top Choice probability is below a calibrated threshold, and measure both agreement of automatic decisions and coverage (share acted on). The cookbook's illustrative 0.60 gate improved TypeSafe agreement from 90.8% to 99.2% while automatically labelling 74.2% of answers; it did not establish accuracy.
97. Compare repeatability with correctness and fallback burden on labelled Coach cases. A consistently wrong route is still wrong; the cookbook itself found Haiku at temperature 0 more repeatable than TypeSafe on that one post. Treat reported 114 ms latency and historical costs as example-specific, and measure Coach's actual response path.

## From "Parallel questions"

98. The worked example sends one 53,777-character document with 13 independent questions (8 Noul, 2 Choice, 3 Score) in one Jev request and compares it with 13 requests that each resend the same document. For Coach, batch independent checks that use the same player utterance and match snapshot; do not split them into repeated requests without a real dependency.
99. In five repeats on `jev-1.12`, the tracked answer values were equal or close within sampling variation across the two batching strategies. This is evidence for that workload, not a guarantee of bit-for-bit equality on every Coach question. Verify Coach-specific answer quality when combining its questions.
100. The cookbook's 12.2x cost and 10.0x time savings rely on a document-dominated 13-question workload; the time figure sums sequential single-call latencies. Concurrent singles reduce wall-time savings but still resend the shared state. Measure Coach's own latency, input/output tokens, and bill because its state length and question count differ.

## From the full "Re-ranking" cookbook

101. This is the worked example behind items 20-24, not a new Coach feature. BM25 searched 3,565 legal passages for 40 queries, and the correct passage was already in every top-30 shortlist. TypeSafe could only reorder those 30. For Coach, measure shortlist recall before judging re-ranking; this example's 100% recall is a property of its selected data, not a general result.
102. One Noul compared each query with each candidate, using explicit true/false criteria to distinguish the specific cited proposition from a merely similar topic. The 40 x 30 setup used 1,200 concurrent calls and sorted the returned nouls. For Coach's answer library, use a precise candidate-fit question and separately check unsupported assumptions; do not read the best relative score as proof the entry is suitable.
103. On these 40 queries, top-1 accuracy rose from 5% to 18%, top-5 from 15% to 35%, and top-10 from 38% to 62%. This makes the top few more useful as Claude context, but 18% top-1 is far too weak to speak the winner automatically. The reported $0.0645 for 1,200 calls uses historical `jev-1.12` pricing; benchmark Coach's own corpus and billing before choosing shortlist size.

## From "Line-by-line search"

104. A Choice over stable line IDs locates the most relevant line in one document, while a separate Noul in the same request asks whether any line actually answers the query. This is a concrete version of Coach's planned rank-plus-fit gate: the Choice winner alone is relative and always exists, even when every candidate is wrong.
105. The cookbook's absent-answer example ranked an irrelevant line at 0.86 while the existence Noul was 0.14; a partial-answer example ranked a line at 0.90 while existence was 0.46. For Coach, distinguish a directly supported prepared answer from a related or partial hint, and give Claude the source text only with its support status. Keep the original source ID/text so the claim can be checked.
106. Its 218-option Choice fits below the documented 255-option limit; a larger library needs filtering or multiple stages, and an early wrong window can hide the right answer. Sending the full 43,980-character document each time is unlike a low-latency voice turn. Evaluate compact candidate shortlists and measure end-to-end latency and answer recall on Coach questions. The cookbook's 0.35/0.70 existence thresholds are examples, not Coach policy.

## From "Function calling"

107. Treat a spoken Coach command as one closed-set tool-route Choice plus typed argument questions over the same utterance. For each fixed enum argument, use a Choice whose keys equal accepted function values; for booleans and members of a list of enums, use Nouls. Validate required arguments and allowed values in Coach code before executing the selected function.
108. Add a separate `stated` Noul for optional parameters so vague words do not force arbitrary values: omit an unstated argument and let the function's documented default apply. Write questions that explain each argument's role, especially when two arguments draw from the same set. Keep free-form numbers, dates, and text on a separate parser or clarification path; this cookbook deliberately leaves them at defaults.
109. The example batches 54 route/argument questions in one request for ten trading functions, then uses only the chosen function's answers. Its reported call confidence is the weakest contributing judgment; retain per-argument probabilities and inspect the weakest before acting. Test this fan-out against Coach's voice latency and token budget rather than assuming 54 questions are cheap in its workload.
110. A plausible function name and legal argument values do not establish that the player requested the action or that it is safe to perform. Keep Coach's per-action confidence gates: low-risk read-only commands can run with a lower bar, while locking or changing a match plan and writing persistent notes need a stronger route/argument check or confirmation. Include an out-of-scope route and test ambiguous, multi-command, and unstated-argument utterances on labelled Coach examples.

## From the full "Skill suggestion" cookbook (repeat)

111. Items 26-31 already cover its two-pass roster search and weak suggestion to Claude. Additional caution from this full example: its `max(fits)` gate checks whether any shortlisted skill seems relevant, then returns the separate Choice winner. It does not require the winner's own fit score to clear the gate; the deck example picks `pptx-author` although `powerpoint` has the higher fit Noul. For Coach's answer-library variant, gate the actual selected answer's suitability, not only the best fit among all candidates.
112. Its reported 16.8% to 7.3% wrong-load and 9.8% to 4.0% needless-load improvements were on 488 synthetic, single-turn Hermes skill requests under one pinned Claude model; it still fixed 37 covered cases and broke 7. Keep candidate suggestions optional and measure Coach's own helped-versus-harmed cases. The Mastodon-to-X mismatch shows an out-of-scope request can survive both checks.

## From "Knowledge graph entity alignment"

113. For pairs of possible duplicate Coach answer-library entries, first create candidate pairs cheaply, then ask one Score with ordered levels `different`, `related/uncertain`, and `same`, plus separate Nouls for field agreement in one request. The middle level sends ambiguous pairs to human review, and component answers explain why. This is for later library cleanup, which remains paused pending the owner's quality/sourcing discussion.
114. Use deterministic comparisons for exact IDs, numeric values, and known game facts; use Jev for semantic differences such as whether two differently worded entries make the same coaching claim. Retain both originals and provenance when reviewing or merging so a mistaken consolidation can be undone.
115. The cookbook rounds a 0-2 Score to the nearest level, implicitly placing decision boundaries at 0.5 and 1.5. Those boundaries are real thresholds even though it says there is no threshold to fit. On its 450 labelled beer pairs it reports route counts (40 merge, 50 review, 360 separate), not precision or recall, so it does not establish that automatic merges are safe. For Coach, test labelled duplicates and require strong evidence or manual approval before changing the library.

## From "Classifying RAG passages"

116. Between retrieval and Claude, score each candidate source passage against the player's actual question with separate Nouls for relevance, usable answer evidence, contradiction of the question's premise, and instruction/prompt-injection content. Keep route policy in code and carry accepted evidence and premise-conflicting evidence in separate, source-ID-labelled blocks. This extends the earlier answer-fit and unsupported-fact checks rather than replacing them.
117. Check injection first and premise contradiction before ordinary answer evidence: a passage that corrects a false premise often contains usable facts too, and should be presented as a correction. Keep all retrieved passages untrusted even if the injection detector scores them low; this detector is not a security boundary. Source type/provenance should remain visible when deciding what to trust.
118. The example sends one request per query-passage pair (12 per query) and four Nouls per request. Its six-query demonstration shows useful behavior, including dropping a planted injection and preserving a source that corrects a false premise, but does not measure corpus-wide answer correctness or false rejection. For Coach's voice path, test latency, shortlist recall, and quality on its own library before deciding how many passages to score; all four example thresholds are corpus-specific.

## From "Double-checking citations"

119. Verify a generated Coach factual claim against the original cited source, not just against a retrieved excerpt. First use code to check that an alleged verbatim quote exists after narrowly defined normalization; then ask a three-way Choice whether its surrounding section supports, contradicts, or says nothing about the exact claim. Preserve source IDs and let uncertain verdicts go to review or a cautious rewrite.
120. The cookbook caught four planted failures among eight RFC citations, but that tiny constructed set does not establish accuracy for League claims. Its exact quote match can wrongly call a shortened or paraphrased quote fabricated. The code also searches all sections for a supplied quote and does not check that it appears in the citation's *claimed* section; add that check if Coach presents precise section citations.
121. Citation support and answer usefulness are separate: a correctly cited fact may still fail to answer the player, be stale for the current patch, or assert unseen match state. Keep the planned fit, source/version, and live-state checks. Running quote and claim verification only where Coach makes a sourced factual assertion should avoid imposing another call on every short coaching line.

## From the full "Guardrails for LLMs" cookbook (repeat)

122. Items 14-19 already capture its input/output batteries, per-hazard routing, severity override, and named policies. Its 10 input and 5 output examples demonstrate the mechanics but do not establish detection accuracy or safety for Coach. Keep the Coach-specific hazards and labelled tests; the cookbook's thresholds (0.35, 0.70, 0.85, severity 2.0) are illustrative.

## From "SDE cascade"

123. For structured facts extracted from player speech or source material, a possible later pipeline is cheap extractor -> one Jev request with per-field error Nouls -> stronger extractor only if any important error flag fires. Frame each Noul as `P(wrong)` and check support, wrong context, omissions, and format separately. Use deterministic schema/enum/date checks in code where possible, and retain the original source alongside extracted fields.
124. The cookbook's worked NYU page contains no registration date, yet the example cheap record has a plausible, schema-valid fabricated description. Jev flagged the unsupported description at 0.95 and off-target at 0.85 while the holistic record judge was 0.56; a `max` over per-field flags above 0.70 escalated. This illustrates why a broad validity check or JSON schema alone misses semantic errors, not proof of calibrated performance. The cheap record was hard-coded for reproducibility rather than generated live in this run.
125. The 100-prompt cost/quality frontier is described as internal TypeSafe results without enough labelled-case detail here to transfer to Coach. Before adding an extra model rung to the live voice path, compare end-to-end latency, cost, missing/incorrect player facts, and unnecessary escalations on labelled Coach utterances. The escalation path adds both verifier and stronger-model latency; keep current simple routes unless a measured gain justifies it.

## From "Date extraction"

126. If Coach later needs to store a player-stated calendar date (for a reminder or planned session), ask Jev for the date's written mode and parts, then resolve the parts with deterministic date code. Pass the date's role, such as `the date of the next review`, so a different date in the same message is not silently substituted. Keep the source utterance, resolved date, reference `today`, and timezone together.
127. The recipe sends seven Choice questions together and takes the minimum confidence of the answers actually used; invalid, absent, or low-confidence results go to review. Its 0.60 threshold and six short examples are demonstrations, not calibration on Coach speech. A 151-year Choice list is expensive and unnecessary when candidate years can be parsed from text first.
128. Relative dates depend on explicit application conventions: `next Thursday` means the following calendar week in this recipe, a bare weekday means the next occurrence on or after today, and an omitted year rolls forward only when the month/day is more than 31 days past. Such rules can surprise players, so clarify ambiguous dates before a persistent action. Game-relative timing (e.g. `in five minutes` or an objective spawn) needs match-clock logic and is not covered by this calendar-date recipe.

## From "Pre-parsed value extraction"

129. When Coach needs an exact value from player speech or trusted source text, find candidate spans with deterministic code, then ask a Choice to select the span serving the requested role, including a `none` option. Copy the chosen original span and parse or normalize it in code. This prevents Jev from inventing or transposing digits *after candidate extraction*, but it cannot recover a number the speech recognizer misheard or a regex omitted.
130. For a transcript with several numbers (a timer, level, gold amount, or objective count), the words around each candidate determine its role; combine a selection question with any needed attribute checks in one Jev request when they share the same state. Verify range and game-state plausibility deterministically, prefer observed game telemetry over spoken guesses, and clarify ambiguous values before saving a plan or note.
131. The cookbook's examples use separate requests for selection, currency/country, and credit/charge even though its Parallel questions recipe supports batching independent checks. Its regex helper deduplicates by value, losing position if an identical span appears twice in different contexts; retain offsets or stable span IDs for Coach. With no regex candidates, do not ask Jev to choose an invented value; use a different extractor or ask the player.

## From "Hierarchical classification"

132. If Coach later has a large, reliable hierarchy of topics or plays, ask a Choice over direct children at each level instead of one enormous flat Choice. Greedy traversal follows only the top child; width-K beam search keeps several plausible paths so later evidence can recover from an uncertain early branch. Log node probabilities and where labelled Coach requests diverge from the correct path.
133. In the four selected examples, width-3 beam search matched all four expected leaves while greedy matched two. This is a demonstration, not an estimated Coach accuracy gain. Beam search cannot recover a correct path pruned out of its K frontier, a missing taxonomy leaf, or an out-of-scope request; preserve `none fits`/fallback and compare against Coach's simpler flat or two-level routes on labelled utterances.
134. The prose describes parallel questions, but the supplied `beam_search` code uses a ThreadPoolExecutor to issue up to K separate `system_one` calls per level, not one batched request with K questions. Concurrent calls may reduce wall time while increasing repeated-state tokens and request count. If implemented for Coach, test actual latency/cost and whether sibling decisions can be batched in one call with stable path IDs.
135. The geometric mean of edge probabilities is a search heuristic that normalizes path length; it is not a calibrated probability that a leaf is correct, and the top/second path-score ratio is not a safety gate by itself. Keep a separate suitability check and clarify or fall back on close paths, especially before a persistent plan change.

## From "Autoresearch feature discovery"

136. This is an offline supervised-learning workflow, not a live Coach routing recipe: an LLM proposes Noul/Score questions over labelled text, Jev turns each example into numeric answers, a downstream model fits the labels, and cross-validated errors/feature importance guide new proposals. Consider only after Coach has enough trustworthy labelled player questions or answer-quality outcomes; keep answer-library generation paused until the owner's sourcing/quality discussion.
137. The wine example used 1,200 development and 800 held-out reviews. One proposal round with 18 questions reached 1.869 held-out RMSE; five rounds with 38 questions reached 1.772, an additional 0.097-point gain (reported paired 95% CI -0.147 to -0.050). Most improvement came from the first feature batch. These figures predict critic wine scores, not Coach helpfulness or gameplay benefit; compare with simple text/metadata baselines on Coach labels.
138. A Score question contributes the expected rubric level and distribution spread; a Noul contributes P(true). Keep question IDs, wording, model version, label provenance, and dataset split fixed when comparing features. Do not infer a feature's causal importance from CatBoost importance or a held-out association; correlated questions and leakage-prone labels can make apparently strong signals misleading.
139. Feature discovery costs one Jev request per row per round (the example has 2,000 rows and five rounds, with each round's new questions batched per row), plus proposal/training work. Use an untouched final test set and a stop rule based on development performance and a request budget. New features should enter Coach's runtime only if they improve a relevant labelled metric enough to justify latency and token cost.

## From "Smart home assistant demo"

140. The demo applies speculative fan-out to a voice command: ask request type, target scope, device type, and action together, then use code to read only answers that apply. For Coach, this supports one shared Jev assessment of player intent and available context, with code gating any downstream action; it adds no new evidence about Coach-specific latency or accuracy beyond the earlier fan-out pattern.
141. The new workflow is compound-request detection: a Noul flags whether one utterance contains multiple distinct actions, an LLM splits it into atomic requests, and Jev assesses each separately. For Coach, preserve the original utterance and order, check the split for omitted or invented actions, and avoid executing or saving a plan from an ambiguous split. General conversation routes to the generative LLM only after the structured assessment.

## From "Models" (checked 2026-10-06)

142. TypeSafe currently lists `jev-1.13.0` as its stable release, with `jev-latest` and `jev-preview` both pointing to it. Coach's `jev_rank()` currently requests `jev-latest` and reads only `answers.next_play`, so a future alias move could change ranking without a Coach code change and the resolved version is not retained there. Before relying on calibrated gates or comparing runs, log the response's versioned `model` and pin a tested version when appropriate.
143. The current published rate is $0.042 per million input tokens with free output tokens; limits are 100,000 tokens/second and 80 requests/second, and TypeSafe says those limits may change. Budget ranking by measured input usage and handle 429/retry-after when using Coach's direct HTTP call; historical `jev-1.12` cookbook prices are not current pricing.
144. Jev 1.13 is text-only and accepts a string, JSON object, or array of text values as state. Coach must turn game frames and speech into reliable text/structured observations first. The published context limits are 64k tokens for a request and 32k for state plus its longest question; trimming noisy playbook/state context matters for both cost and answer quality.
145. English is TypeSafe's best-supported language; validate non-English player speech separately. The model page says customer requests/responses are not used for training, while zero data retention is an enterprise option; check the linked legal terms before sending sensitive player data. Source: https://docs.typesafe.ai/models

## From "API reference"

146. The HTTP contract is `POST /v1/systemone` with required `state`, `model`, and a named map of typed `questions`; answer IDs match question IDs, but the ID itself is not used in model inference. `Choice` supports at most 255 options, `Score` 2–10 ordered levels, and `Noul` returns P(yes). These bounds should be validated when dynamically building Coach questions.
147. A response includes the resolved versioned `model`, per-question answers, and `usage.input_tokens`/`usage.output_tokens`. `Choice` returns the winning option, all option probabilities, and confidence. Coach's `jev_rank()` currently discards the model/usage metadata and returns only option probabilities; retain model and input usage in observability before calibrating rank gates or estimating cost.
148. The API documents 401 for authentication, 422 for malformed requests, and 429/529 for rate limiting or overload. Its SDK retries 429/529 with backoff; Coach uses direct `urllib` and currently treats an HTTP error as Jev unavailable. A bounded retry honoring `Retry-After` could improve resilience, but must fit Coach's voice-response deadline and preserve its current safe fallback. Do not retry a 401 or 422 as a transient failure.
149. Coach maps a missing probability to zero in `jev_rank()`. If a 200 response omits or malforms `answers.next_play.probabilities`, zeroing every option could silently create an arbitrary ranking. Validate answer type, expected option keys, finite nonnegative probabilities, and approximate sum before using a response; otherwise use the existing unavailable fallback. Source: https://docs.typesafe.ai/api

## From "Agent skill"

150. TypeSafe publishes an optional coding-agent skill, but this documentation page by itself does not require installing it. The practical review advice is to keep question wording and numeric thresholds together, check them against labelled Coach cases, and validate proposed API fields against the live reference. The TypeSafe skill is available at https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md if explicitly adopted later.
151. The page says to choose the option with the highest "confidence" when no threshold is needed. In a Choice response there is one confidence value for the whole answer and a probability for each option; choose the highest-probability option (`choice`) and use answer confidence only to decide whether to trust or act on that selection. Coach's top-two play ranking appropriately reads option probabilities rather than comparing nonexistent per-option confidence values. Source: https://docs.typesafe.ai/agent-skill

## From "Legal"

152. This page is an index to TypeSafe's Data Processing Agreement (https://typesafe.ai/legal/data-processing), Master Customer Agreement (https://typesafe.ai/legal/mca), and Privacy Policy (https://typesafe.ai/legal/privacy-policy). It repeats the stated no-training commitment and says enterprise zero data retention is available. It does not itself specify ordinary-account retention terms, so review the applicable agreements before setting a Coach player-data policy. Source: https://docs.typesafe.ai/legal

## From "Jev 1.13 jaggedness" (reviewed by TypeSafe 2026-10-02)

153. TypeSafe warns that `jev-1.13` can read instructions very literally and struggles with multi-hop or double-negative judgments. Coach's `next_play` question currently combines safety, reset, lane tempo, objectives, unknown observations, and player plan in one long instruction. On labelled edge cases, test whether each condition is applied as written; move deterministic conditions into code and, if needed, split independent semantic checks into separate questions with aligned criteria.
154. Jev is unreliable for counting, arithmetic, numeric proximity, and date/time ordering; Score expectations are not precise measured quantities. Compute timers, gold/item thresholds, level/CS differences, objective windows, and date comparisons in Coach code, passing named buckets or computed facts when Jev needs to judge their meaning. Extract ambiguous text parts with closed-set questions only when code cannot find them directly.
155. Unrelated state can reduce Jev 1.13 accuracy. Coach currently sends a ranking state that may contain game facts, a long plan, champion kits, role principles, a coordinator briefing, lane fundamentals, minimap facts, and recognized plays. Measure token usage and ranking quality with an ablation that removes irrelevant fields, while retaining the observations needed to avoid invented claims. Treat player questions and retrieved text in state as untrusted data because adversarial instructions there can influence Jev.
156. TypeSafe reports a first-option bias in some Choice questions. Coach builds `next_play` criteria from its option tuple; offline tests should permute the same options while holding state and wording fixed, compare full probability distributions, and log how often the top-two plays change. Keep runtime option order deterministic until that sensitivity is measured. Source: https://docs.typesafe.ai/model-jaggedness/jev-1.13

## Owner's note: growing the answer library

36. The library needs more and better entries, and the first attempt (agents writing thousands of entries) used a lot of tokens for quality the owner doubts. Before generating more, discuss with the owner how to get entries more efficiently and how to check their quality. Not decided; the library job stays paused until then.

## From our own tests (2026-10-06)

10. Ask Claude for the spoken line only; fetch follow-up lines only on "explain more". The all-in-one prompt took 29 to 70 seconds; a minimal call takes about 3.
11. Have Jev check every line Claude writes, including follow-ups, for invented facts and numbers.
12. When the player asks for options, Claude may not reuse a prepared answer verbatim.
13. A prepared answer that presupposes something unobserved can still rate high; add a guard for that before speaking it.
