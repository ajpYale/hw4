# AI Prompts — Homework 4 (Campus Customs Shop + Chatbot)

Andrew Perlowin

---

## Problem 2 — Analyze the database

**Prompt 1**

> Look at the database in data/campus_customs and figure out what tables are in it and what each field is for. Start output/harness.md and write down the tables, their fields, and one line on why each field matters for the shop + chatbot.

**What the first prompt was missing:** this worked

---

## Problem 3 — Build the Campus Customs website

**Prompt 1**

> Build the Campus Customs storefront in React + TypeScript + Vite. Nav bar with Home, Products, About Us, Log in, Create account. The Products page should show every item from the catalogue with its image, name, price and a short description, and clicking one opens a single-item page with the big image on one side and the full details on the other. Put a chat box in the bottom right. Write the Home and About copy in a Campus Customs voice and use original wording, don't copy real stores

**What the first prompt was missing:** The first version of the category filter used the raw `garment_type` column, so clicking "Hoodies" showed 5 products out of the 27 the store actually sells. I had it add a normalizing map from the 22 raw strings onto six real categories.

**Follow-up prompt**

> Hoodies shows only 5 things, why and fix

---

## Problem 4 — Create account and login

**Prompt 1**

> Make the Create account and Log in pages actually work. account takes first name, last name, email, password and a confirm field, and saves the new user to the users table. Log in takes email and password. Passwords have to be stored securely, so no plain text

**What the first prompt was missing:** it said "securely" without saying *which* scheme,
and the database already had three users whose passwords were hashed by the course's
own seeding script. A fresh choice like bcrypt would have been more secure in the
abstract but would have made the grader's test account impossible to log into, because
its stored hash was made a different way.

**Follow-up prompt**

> Before you pick a hashing library, work out exactly how the seeded users' passwords were hashed, and match it. The test@campuscustoms.yale.edu account has to still work with the password `password`.

The stored format was `pbkdf2_sha256$salt$hash` with no iteration count recorded in the
string, so the assistant brute-forced the count against the known test password and
found **120,000 iterations, hex-encoded**. New signups now use the identical scheme, so
there is one verification path and the seeded user logs in without a special case.

**A third thing I asked about.** I asked how the site should remember who is logged in,
since Problem 8 needs the chatbot to know the customer. We went with a signed HttpOnly
cookie rather than a token in `localStorage`, so the browser cannot read the session
and cannot edit it to impersonate another shopper — the agent's idea of who it is
talking to comes from a signature the server checks, not from a number the page sends.

---

## Problem 5 — PydanticAI agent backend

**Prompt 1**

> Build the shop chatbot as a PydanicAI agent and connect it to the chat box on the site. Keep it as four files in backend/: prompts/prompt for the system prompt, agent.py, tools.py and models.py. Add a chat route to main.py so a message from the website comes back answered. Use the Portkey key from the .env in the folder above this one, and the gpt luna

**What the first prompt was missing:** it said to connect the agent but not what a
reply *is*. Left alone, the obvious build has the model write a sentence listing
products it remembers, which is exactly how a chatbot ends up quoting a price that is
not in the database.

**Follow-up prompt**

> Don't make things up stop that

---

## Problem 6 — Tools for product info and stock

**Prompt 1**

> Give the agent tools that look up information from the database: a product's description, its price, and how many are in stock, by size when the customer asks. It must not make up prices or quantities, and if a size is sold out it has to say so

**What the first prompt was missing:** it described what the tools should fetch but not
what shape to hand back, and the first version returned a plain list of sizes with
quantities. The agent then had to notice on its own that `quantity: 0` means "do not
promise this," which is exactly the kind of inference a model gets wrong under pressure.

**Follow-up prompt**

> Make the honest answer the easy one. Return sold-out sizes as their own separate
> list rather than making the model work it out from the numbers.

`StockAnswer` now splits `sizes_in_stock` from `sizes_sold_out`. Asked about an XL that
has zero on hand, the assistant replies: *"No — XL is sold out in the Baseball Left
Chest Crewneck. We have S, M, L, and XXL available,"* which matches the database row
for row.

**The bug this problem actually turned up.** Asked "what hoodies do you have?", the
assistant answered "we have six hoodie designs." It was reading the length of the
capped result list. The shop sells twenty-seven. The search tool now returns a true
`total_matches` alongside the sample, and the answer is correct.

---

## Problem 7 — Chat search that updates the page

**Prompt 1**

> When someone asks about a type of item in the chat, the agent should search the catalogue and the website should show the matching products as cards with the image, name, andd prices

**What the first prompt was missing:** nothing

---

## Problem 8 — Customer memory

**Prompt 1**

> Save the chat history for logged-in customers in the database and load it back when they return. The agent should know the name and email of whoever it is talking to and if they are on a product page it should understand what "this" refers to

**What the first prompt was missing:** it did not say where the agent's idea of the
customer should come from. The easy build has the browser send a `user_id` along with
the message, which means anyone can edit one number in a request and have the
assistant treat them as a different customer.

**Follow-up prompt**

> The agent should get the customer's identity from the signed session cookie on the
> server, never from anything the page sends. The browser should only be trusted to
> say which product page it is on.

So the request carries `page_path` and `product_id` — harmless facts about where the
shopper is — while *who they are* is resolved server-side from the signed cookie.

**A choice I made against the suggestion.** I was advised to reuse the seeded
`chat_messages` table, which already had the right columns. I asked for a new
`chat_history` table instead, and it earned its place: `chat_messages` has nowhere to
record which page a customer was on, and page context is part of what this problem is
about. The new table stores `page_path` and `product_context` alongside each message.

**On cost.** I asked how much of the old conversation gets resent to the model each
time, and capped it at the last 10 messages. Without a cap, every message in a long
session resends the entire history and the cost of a single reply grows without limit.

---

## Problem 9 — Usability improvements

**Prompt 1**

> Add two usability improvements to the front end and two to the agent or backend, and write them up in output/usability.md saying what each one is and why it helps a Campus Customs clieant

**What the first prompt was missing:** it invited a list of plausible-sounding ideas.
Four generic improvements written up well would read fine and change nothing about the
site, which is exactly what the assignment warns against.

**Follow-up prompt**

> Only pick things that fix something actually wrong with the site right now. Show me
> the before and after for each one, and for the backend ones measure the difference
> rather than asserting it.

That rule produced all four, and each came from something visible:

1. **Markdown in chat replies** — the assistant's prices were rendering as literal
   `**$72**` asterisks on screen.
2. **Stock badges on product cards** — you could only learn your size was gone by
   opening the product page and going back.
3. **In-memory catalogue index** — every search re-read 102 rows and re-parsed 204
   JSON fields for static data. Measured at **34× faster** once cached.
4. **No dead-end searches** — "quarter-zips under $70" answered "we don't have any"
   when the cheapest is $72. It now says so and offers the 11 we carry.

**A bug the screenshots caught.** After adding the stock badges, every product card
restored from saved chat history displayed "Sold out" — including items with five
sizes in stock. Old history rows had stored a copy of each product from before the
stock field existed. The fix was to stop trusting stored card data at all: history now
keeps only the `product_id` and rebuilds the card from the catalogue, so a reopened
conversation shows current stock rather than a snapshot.

---

## Problem 10 — Style the website

**Prompt 1**

> Restyle the site so it feels like a real Campus Customs storefront rather than a default template

**What the first prompt was missing:** no point of view. "Make it look good" produces
a tidier version of the same generic store, and this problem explicitly rewards
imagination.

**Follow-up prompt**

> Let's go vintage — I want artificial aging so it almost looks like an old book.
> Keep it mostly gold and blue.

That gave the whole thing a spine: the site is set as an aged nineteenth-century
mail-order catalogue. Cream paper with sun-warmth in the corners, foxing spots, an
edge vignette, and a grain layer generated with SVG turbulence so there is no image
file to download. Playfair Display headings over EB Garamond body, a letterpressed
masthead, products mounted as catalogue plates, the product page laid out as a book
spread with a gutter rule, and the About page opening on an illuminated drop cap.

**The decision I'm most glad we made.** I was asked whether the aging should cover the
product photographs too. It should not, and the site now follows one rule: **the aging
is applied to the page, never to the garment.** Every product sits in a pure white
window inside its aged mount. A sepia wash over everything would have looked more
convincingly antique and would have lied about the color of the merchandise — someone
choosing between heather gray and charcoal has to see the real thing.

**A bug worth recording.** The first drop-cap rule was `.prose > p:first-of-type`,
which put an enormous gold **A** on the small-caps overline reading "ABOUT US" — that
overline is also a paragraph. Changing the selector to target the paragraph following
the heading fixed it.

**A second pass.** Looking at the result I asked to push it further — *"make it look
older, text should be kind of calligraphic."* The typefaces changed to IM Fell English
(a digitization of 1680s letterpress, with the ink spread left in) over Cormorant
Garamond, with the shop's name set as an engraved copperplate script. The paper went
from cream to properly yellowed, with heavier foxing, a water stain, a long-settled
horizontal fold, and nearly double the grain.

---

## Problem 11 — Site testing

**Prompt 1**

> Test the live site and put the evidence in output/app_check.html — screenshots of the chat checking inventory, the search cards appearing, and one of the Problem 9 features, each with a short caption

**What the first prompt was missing:** a screenshot proves a screen existed, not that
the number on it was true. A fabricated stock level and a real one look identical in a
JPEG, and "the agent must not invent inventory" is the thing this homework keeps
testing.

**Follow-up prompt**

> For every number visible in a screenshot make sure it is a real number from data

**A real bug the screenshots caught.** Setting up the first screenshot, I asked the
assistant "how many of this do you have left in each size?" while standing on a
product page, and it replied "Which product would you like me to check?" Page context
had never worked from the browser at all — it had only ever worked in direct API tests
where the product id was passed by hand. The chat widget is mounted outside `<Routes>`
so that it survives navigation, which means it has no route match and `useParams()`
was always empty. Reading the id from the path fixed it.

---

## Problem 12 — Audit trail, safety, finishing the harness

**Prompt 1**

> Keep an append-only audit trail of the agent's tool calls in output/audit_trail.json
> with the time, tool name, arguments, result and stop reason. Add safety rules to prompt and harness

**What the first prompt was missing:** it described safety as something you write in a
prompt. A prompt rule is a request to a model that can be argued with; it is not a
guarantee.

**Follow-up prompt**

> Separate the safety that depends on the model behaving from the safety that doesn't.
> For anything important, I want it enforced in code rather than asked for in the
> prompt.

`harness.md` now says plainly which is which. Three protections hold regardless of what
the model does: product cards are rebuilt from SQLite so a hallucinated price cannot
reach the screen; customer identity comes from a signed cookie so it cannot be forged
by editing a request; and `UserPublic` has no `password_hash` field so a credential
cannot enter the context window at all. The prompt rules sit on top of that, not
underneath it.

**On the audit trail being genuinely append-only.** It was wired into the tools when
the first one was written rather than bolted on at the end, so it has been recording
throughout. It currently holds 19 entries spanning half an hour and several server
restarts, including the one upstream content-filter rejection, logged as
`stop_reason: model_error`.

---
