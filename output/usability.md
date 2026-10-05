# Usability improvements

Four changes to the running Campus Customs site — two on the front end, two in the
agent and backend. Each one is live in the app, not a plan.

---

## Front end 1 — The assistant's replies render as formatted text

**What I added.** Assistant messages in the chat panel are rendered as Markdown instead
of raw text. User messages are still rendered as plain text, deliberately.

**What was wrong before.** The model writes prices in bold, and the shopper saw the
asterisks: `The cheapest quarter-zips are **$72**`. Lists arrived as a wall of
`- item` lines with no bullets. The single most important thing in the message — the
price — was the thing wrapped in punctuation.

**Why it helps.** Prices, product names and size lists now stand out at a glance, and
multi-item answers read as lists instead of a paragraph. A shopper skimming a reply
finds the number they care about immediately.

**Why user messages stay plain.** Rendering shopper-typed text as Markdown would let
anything they paste become formatted markup inside the page. Their own words are shown
exactly as typed.

---

## Front end 2 — Stock is visible on the product card, before the click

**What I added.** Every product card carries an availability badge. A product with
three or fewer sizes left shows the specific sizes in gold — `Only S, M, XL`. One with
nothing left shows a dark `Sold out`. Cards with full availability show no badge, so
the badge always means something.

**What was wrong before.** Availability only appeared on the product detail page. A
shopper who wears XL had to open an item to learn XL was gone, then go back, then open
another. Across a 27-item hoodie grid that is a lot of dead clicks.

**Why it helps the business.** It steers people toward items they can actually buy, and
the gold "Only S, M, XL" badge does honest scarcity work — it is true, it comes from
the live `inventory` table, and it gives a shopper who wears M a reason to decide now.

**A bug this surfaced.** Chat cards restored from saved history were all showing
"Sold out." Old rows had stored a snapshot of the product taken before the stock field
existed. Rather than patch the old rows, history now trusts only the stored
`product_id` and rebuilds each card from the catalogue — so a conversation reopened
next week shows next week's stock, not a fossil.

---

## Agent / backend 1 — The catalogue is indexed in memory

**What I added.** The 102-row catalogue is read once, parsed once, and held in memory
as a pre-weighted search index. Every chat search scans that instead of hitting SQLite.

**What was wrong before.** Each search re-read all 102 rows and re-parsed two JSON
columns per row — 204 `json.loads` calls — to answer a question about static data.

**Measured.** Building the index takes 2.5 ms. A cached search takes 0.1 ms, which is
**about 34× faster**. The assistant often searches more than once in a turn, so the
saving compounds on exactly the replies that are already slowest.

**Why it helps.** The shopper waits less. The model's own latency dominates a reply, so
removing avoidable work on our side is the part we control.

---

## Agent / backend 2 — The assistant never dead-ends a shopper

**What I added.** When a search returns nothing, the tool attaches an `alternatives`
object: if the category exists but the filter excluded everything, it reports how many
we carry and the real cheapest price; if we do not stock the category at all, it
returns what we do sell. `prompt.md` instructs the agent to use it.

**What was wrong before.** A genuine exchange from testing:

> **Shopper:** show me quarter-zips under $70
> **Assistant:** We don't have any quarter-zips under $70 right now.

True, and useless. The cheapest is $72. A customer two dollars from a sale was shown a
closed door.

**After:**

> **Assistant:** We don't have any quarter-zips under $70 — the least expensive
> quarter-zip is $72. We carry 11 quarter-zip designs if you'd like to browse them.

And for something we genuinely do not stock:

> **Shopper:** do you sell baseball caps?
> **Assistant:** We don't carry baseball caps right now. We do sell hoodies, crewnecks,
> T-shirts, quarter-zips, jackets, and performance gear.

**Why it helps the business.** Every "no" now carries a next step. The assistant stays
honest — it never claims we have something we do not — but an unmatched search becomes
a redirection instead of the end of the conversation.
