---
name: product-size
description: Measure a real product (a can, a bottle, a jar, a phone) in millimetres in AI-generated stills and takes, by the eyes of the person holding it, and catch a product drawn too big, too small, stretched, or changing size between shots. Use before buying video from a still that shows a product, when someone says the product looks too big, or when planning a product shot.
---

# Product size

Image models draw products too big, and size words in a prompt ("a 12 oz can", "fits in her hand") don't hold it. On
real reels a 66 mm can came out 1.25 to 1.6 times its size, and its size changed from shot to shot. A vision model
asked "is this the right size?" mostly guesses. Measured, it's arithmetic: adult pupils sit about 63 mm apart, so the
face of the person holding the product is a ruler.

## Set up once
Write a product card, for example `product.toml`:

```toml
[product]
what = "a soda can"        # the words the detector looks for
size_mm = [66, 122]        # the real width and height
ref = "renders/can.png"    # optional: the real product, for the review sheet
```

Ask the user for the real size. Never guess it from a picture.

## Measure every still before it becomes video
`uv run scripts/size.py <still|clip> [...] --card product.toml --sheet size_sheet.jpg`, inputs in cut order.

- **PASS**: within 0.8-1.2x of the real width. A product held at the chest sits nearer the lens than the eyes and
  reads up to ~15% big; the tolerance covers it.
- **FAIL size**: re-roll or fix the still. Never buy a take from it.
- **FAIL jump**: the product changed size by more than 15% from one shot to the next.
- **FAIL shape**: the product is stretched.
- **FLAG**: not in a hand (on a table, in the air). Its distance to the lens is unknown: judge it on the sheet.
- **INFO**: no face to scale it (an insert), or no product found. Judge it on the sheet or by eye.

The sheet puts the real product at true scale beside the one in the frame. Give it to the blind review: with the
sheet, Claude judged size right 10 times out of 10; from bare frames, 5 out of 10.

## When the product is too big
1. Start the shot with the product on a table at true size and let the take lift it.
2. Or paste the real product into the still at the measured scale before animating it. Hands over the product make
   this fragile: check the result at full size.
3. A product close-up is a still of the real product with a slow push-in, never a generated take.

Prompt words rarely fix size. After two failed fixes, change the shot: hands out of frame, the product on the table.

## Limits
- No face in the frame, no scale.
- The width stays the same at any tilt only for round products. A box turned edge-on reads narrow.
- Glass and very thin objects are found less reliably. Check the sheet.
- A face turned past ~60 degrees gives no scale.
- The ruler is an adult face: children and extreme close-ups read off.
