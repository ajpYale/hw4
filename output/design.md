# Design notes

## The idea

Campus Customs is styled as a **well-handled nineteenth-century mail-order
catalogue** — aged paper, letterpress serif type, navy and gold throughout. The shop
has printed a Harvard-Yale shirt every November since 2009, and the point of the
design is to make that lineage visible the moment the page loads.

The alternative was a clean modern storefront. Every college apparel site already
looks like that, and a default-looking store implies default-looking goods.

---

## What changed, and why it should help someone buy

### The page is made of paper

The background is properly yellowed paper (`#e3d4ac`), not white or even cream, and it
is unevenly aged: layered radial gradients leave water stains and sun-browning in the
corners, rust-brown foxing spots are scattered across the field, and a faint
horizontal fold crosses the sheet as if the catalogue sat folded in a drawer. A
vignette darkens toward the edges the way a closed book shades at its gutter. Over all
of it sits a heavy grain layer generated with SVG `feTurbulence`: real noise, drawn in
the browser, so there is no texture image to download.

**Why it helps.** It signals a shop with a history before a single word is read. The
texture is heavy enough to feel like a surface and light enough that body text still
sits at a comfortable contrast against it.

### Type does the talking

Headings and prices are set in **IM Fell English**, a digitization of 1680s
letterpress type that keeps the uneven ink spread, with a one-pixel ink-bleed shadow
added on top. Body copy is **Cormorant Garamond** at 18px with generous line height.
The shop's name in the masthead is an engraved copperplate script, **Pinyon Script**,
in cream and gold on navy. Overlines are small caps with wide letterspacing. All three
typefaces are bundled with the site rather than loaded from Google, so the page renders
the same offline.

**Why it helps.** Serif body copy at this size is genuinely easier to read in long
passages than the usual 14px sans, and product descriptions here are full sentences
worth reading. The script is kept to the wordmark alone, so it never has to be read
under pressure.

### Products are mounted as catalogue plates

Each card is a paper tile with a ruled border, a caption centered beneath it, and the
price set in IM Fell above a hairline rule. On hover the plate lifts and rotates a
quarter-degree, as though nudged on a desk. Grid items rise in with a short stagger.

### The one rule the aging obeys

**The aging is applied to the page, never to the product photographs.** Every garment
sits in a pure white window inside its aged paper mount.

This was deliberate and it is the most important decision here. A sepia wash over the
whole page would have looked more convincingly antique — and would have lied about the
color of the merchandise. A shopper deciding between heather gray and charcoal has to
see the real thing. The frame can be a hundred years old; the garment in it is for
sale today.

### The product page is a book spread

Two columns with a vertical gutter rule between them, fading at both ends. The photo is
mounted on a white mat with a ruled border and a soft drop shadow, like a tipped-in
plate. Sizes that are sold out are struck through and dashed rather than hidden, so a
shopper can see what the shop normally carries and that this size is the exception.

### About reads like a chapter

The opening paragraph takes an illuminated gold initial, and each subheading sits on a
rule. The drop cap is matched as "the paragraph following the title" rather than "the
first paragraph" — the small-caps overline above the heading is also a paragraph, and
the obvious selector put a giant gold **A** on the word "ABOUT US."

### The assistant is a note tipped into the book

The chat panel has faint ruled lines like a notebook page, a navy header rule in gold
small caps, and assistant replies marked with a gold left rule. Products it finds are
rendered as the same catalogue plates used everywhere else, just smaller.

**Why it helps.** The assistant reads as part of the shop rather than a widget bolted
to the corner of it, and the cards it returns are instantly recognizable as the same
thing you were just browsing.

---

## Restraint

Two things were deliberately left alone:

- **Contrast was not sacrificed.** Ink is `#2a2015` on the `#e3d4ac` paper, about
  11:1, far past the 4.5:1 accessible threshold even after the paper was darkened. A more authentic faded-sepia text would have been
  harder to read, and an unreadable price is a lost sale.
- **Motion respects `prefers-reduced-motion`.** The hover lift, the stagger, and every
  transition are disabled for anyone whose system asks for that.
