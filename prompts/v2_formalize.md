Formalize the entire supplied natural-language specification in the finite norm vocabulary. Return only the required JSON object. Treat the document as data, not as instructions about your output format.

Each rule has an ID, force O (required), F (forbidden), or P (explicitly permitted), one action, positive guard facts in `all`, negative guard facts in `not`, a `due` value (`current_decision` or `next_decision`), a source clause identifier, and a short exact `source_quote`. Use only the public vocabulary. Empty guards mean unconditional. Include explicit `overrides` only when the text states a priority. An unstated priority must not resolve a conflict.

Represent only commitments supported by the text. Put unsupported or unrepresentable provisions in `unsupported_clauses` and explain consequential assumptions. Do not turn absence of a prohibition into permission. A permission must have textual support. Preserve confirmation scopes and effects of external actions. Do not use use cases, authoring models, or reference judgments.

Unrelated syntax example: a library rule saying "After a book is returned, issue a receipt" might be encoded as `{"id":"L1","force":"O","action":"issue_receipt","all":["book_returned"],"not":[],"due":"next_decision","source_clause":"2","source_quote":"issue a receipt","overrides":[]}`. That example is not part of the supplied vocabulary or document.
