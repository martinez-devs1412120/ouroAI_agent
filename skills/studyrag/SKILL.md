# Skill: studyrag

**What it is.** Reads the user's personal study notes from their StudyRag vector store. The store is a TF-IDF index built by their separate StudyRag project; this skill loads it read-only and returns the top relevant passages.

**When to use FIRST.** Any question about the user's own files, notes, slides, handouts, or coursework — including questions that name a specific file (e.g. "what is jayar.pptx about?"). Always check the user's notes before falling back to the web; their notes are more relevant than a generic search.

**When NOT to use.** General world knowledge → use `web_search`. Math → use `calculator`. Anything outside the user's indexed materials.

**Worked example.**
- User: "What do my notes say about recommendation systems?"
- Step 1: call `query_studyrag(question="recommendation systems")` → returns up to 4 chunks with source filename and relevance score.
- Step 2: synthesize the chunks into a structured answer. **Cite the source filename** in your response.

**Reliability notes.** TF-IDF matches words in the slide text — filenames themselves aren't indexed. A query like "what is jayar.pptx about?" won't match the deck's content; ask about the *topic* instead, e.g. "what do my notes say about recommendation systems?" The tool also rejects chunks with relevance < 0.01 (zero word overlap) to avoid feeding the model unrelated noise.
