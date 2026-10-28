// The catalog is intentionally synthetic and has no image column. These stable,
// category-appropriate Unsplash photos give products a useful visual treatment
// without inventing brand-specific product photography.
const PHOTO = (id) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=900&q=82`;

const TYPE_IMAGES = {
  watch: PHOTO("photo-1523275335684-37898b6baf30"),
  smartwatch: PHOTO("photo-1523275335684-37898b6baf30"),
  camera: PHOTO("photo-1516035069371-29a1b244cc32"),
  speaker: PHOTO("photo-1608043152269-423dbba4e7e1"),
  headphones: PHOTO("photo-1505740420928-5e560c06d30e"),
  tablet: PHOTO("photo-1544244015-0df4b3ffc6b0"),
  monitor: PHOTO("photo-1527443224154-c4a3942d3acf"),
  keyboard: PHOTO("photo-1587829741301-dc798b83add3"),
  sneakers: PHOTO("photo-1542291026-7eec264c27ff"),
  "running shoes": PHOTO("photo-1542291026-7eec264c27ff"),
  backpack: PHOTO("photo-1553062407-98eeb64c6a62"),
  jacket: PHOTO("photo-1551488831-00ddcb6c6bd3"),
  dress: PHOTO("photo-1595777457583-95e059d581b8"),
  scarf: PHOTO("photo-1601924994987-69e26d50dc26"),
  sunglasses: PHOTO("photo-1511499767150-a48a237f0083"),
  kettle: PHOTO("photo-1594212699903-ec8a3eca50f5"),
  toaster: PHOTO("photo-1584776296944-ab6fb57b0bdd"),
  blender: PHOTO("photo-1570222094114-d054a817e56b"),
  lamp: PHOTO("photo-1507473885765-e6ed057f782c"),
  cookware: PHOTO("photo-1556911220-bff31c812dba"),
  "pet bed": PHOTO("photo-1548199973-03cce0bbc87b"),
  "cat toy": PHOTO("photo-1519052537078-e6302a4968d4"),
  "chew toy": PHOTO("photo-1587300003388-59208cc962cb"),
  "water bottle": PHOTO("photo-1602143407151-7111542de6e8"),
  "yoga mat": PHOTO("photo-1592432678016-e910b452f9a2"),
  tent: PHOTO("photo-1504851149312-7a075b496cc7"),
  "comic book": PHOTO("photo-1612036782180-6f0b6cd846fe"),
  notebook: PHOTO("photo-1531346878377-a5be20888e57"),
  novel: PHOTO("photo-1512820790803-83ca734da794"),
  perfume: PHOTO("photo-1541643600914-78b084683601"),
  shampoo: PHOTO("photo-1556228720-195a672e8a03"),
  "face cream": PHOTO("photo-1611930022073-b7a4ba5fcccd"),
  "car vacuum": PHOTO("photo-1551830820-330a71b99659"),
  drill: PHOTO("photo-1504148455328-c376907d081c"),
  "plush bear": PHOTO("photo-1559454403-b8fb88521f11"),
  jeans: PHOTO("photo-1542272604-787c3835535d"),
  "pet bowl": PHOTO("photo-1589924691995-400dc9ecc119"),
  curtains: PHOTO("photo-1616486338812-3dadae4b4ace"),
  pillow: PHOTO("photo-1584100936595-c0654b55a2e2"),
  "bicycle helmet": PHOTO("photo-1558981806-ec527fa84c39"),
  "jump rope": PHOTO("photo-1599058917212-d750089bc07e"),
  dumbbells: PHOTO("photo-1583454110551-21f2fa2afe61"),
  "sleeping bag": PHOTO("photo-1504280390367-361c6d9f38f4"),
  doll: PHOTO("photo-1596461404969-9ae70f2830c1"),
  "art set": PHOTO("photo-1513364776144-60967b0f800f"),
  "lip balm": PHOTO("photo-1586495777744-4413f21062fa"),
  razor: PHOTO("photo-1621607512214-68297480165e"),
  "hair dryer": PHOTO("photo-1522338242992-e1a54906a8da"),
  vitamins: PHOTO("photo-1607619056574-7b8d3ee536b2"),
  vacuum: PHOTO("photo-1558317374-067fb5f30001"),
  "floor mats": PHOTO("photo-1503376780353-7e6692767b70"),
  "seat cover": PHOTO("photo-1503736334956-4c8f8e92946d"),
  "tire gauge": PHOTO("photo-1485965120184-e220f721d03e"),
  "phone holder": PHOTO("photo-1511707171634-5f897ff02aa9"),
  "dash camera": PHOTO("photo-1493238792000-8113da705763"),
  
  toolbox: PHOTO("photo-1530124566582-a618bc2615dc"),
  ladder: PHOTO("photo-1586864387967-d02ef85d93e8"),
  pruner: PHOTO("photo-1416879595882-3373a0480b5b"),
  "garden hose": PHOTO("photo-1558904541-efa843a96f01"),
  cookbook: PHOTO("photo-1495521821757-a1efb6729352"),
  dictionary: PHOTO("photo-1524578271613-d550eacf6090"),
  planner: PHOTO("photo-1517842645767-c639042777db"),
  calendar: PHOTO("photo-1506784983877-45594efa4cbe"),
  audiobook: PHOTO("photo-1478737270239-2f02b77fc618"),
  "bird feeder": PHOTO("photo-1552728089-57bdde30beb3"),
  "cookware set": PHOTO("photo-1556911220-bff31c812dba"),
};

// Reuse only semantically adjacent product-type assets before using a broader
// department or global fallback. These are representative images, not claims
// that the photograph is the exact catalog item.
const RELATED_TYPE_IMAGES = {
  "building blocks": ["doll", "plush bear"],
  "remote car": ["doll", "plush bear"],
  puzzle: ["doll", "plush bear"],
  "card game": ["doll", "plush bear"],
  "board game": ["doll", "plush bear"],
  "dog leash": ["pet bowl", "pet bed", "cat toy"],
  "pet carrier": ["pet bed", "pet bowl", "cat toy"],
  "fish tank filter": ["pet bowl", "cat toy"],
  charger: ["phone holder", "keyboard"],
  "car charger": ["phone holder", "keyboard"],
  flashlight: ["toolbox", "ladder", "drill"],
  hammer: ["toolbox", "ladder", "drill"],
  "paint roller": ["toolbox", "drill", "pruner"],
  sunscreen: ["face cream", "perfume"],
  "wax kit": ["face cream", "perfume"],
};

// Kept for validation/reporting: every current catalog type has a dedicated
// or related candidate. A placeholder is only reached if all candidates fail.
export const UNAVAILABLE_TYPES = new Set();

const DEPARTMENT_IMAGES = {
  electronics: PHOTO("photo-1498049794561-7780e7231661"),
  fashion: PHOTO("photo-1445205170230-053b83016050"),
  "home & kitchen": PHOTO("photo-1556911220-bff31c812dba"),
  "pet supplies": PHOTO("photo-1450778869180-41d0601e046e"),
  "toys & games": PHOTO("photo-1596461404969-9ae70f2830c1"),
  "sports & outdoors": PHOTO("photo-1461896836934-ffe607ba8211"),
  "beauty & health": PHOTO("photo-1596462502278-27bfdc403348"),
  "books & media": PHOTO("photo-1495446815901-a7297e633e8d"),
  automotive: PHOTO("photo-1503376780353-7e6692767b70"),
  "garden & tools": PHOTO("photo-1416879595882-3373a0480b5b"),
};

function firstValidImage(product) {
  for (const key of ["image_url", "imageUrl", "image", "thumbnail_url", "thumbnail"]) {
    const value = product?.[key];
    if (typeof value === "string" && /^https?:\/\//i.test(value)) return value;
  }
  return null;
}

function pushCandidate(candidates, src, source) {
  if (src && !candidates.some((candidate) => candidate.src === src)) candidates.push({ src, source, generic: source !== "product" && source !== "product_type" });
}

export function resolveProductImageCandidates(product) {
  const candidates = [];
  const productImage = firstValidImage(product);
  pushCandidate(candidates, productImage, "product");
  const type = String(product?.product_type || "").trim().toLowerCase();
  const dept = String(product?.department || "").trim().toLowerCase();
  pushCandidate(candidates, TYPE_IMAGES[type], "product_type");
  for (const relatedType of RELATED_TYPE_IMAGES[type] || []) pushCandidate(candidates, TYPE_IMAGES[relatedType], "related_type");
  pushCandidate(candidates, DEPARTMENT_IMAGES[dept], "department");
  // Last-resort valid asset: it is still preferable to a blank card, and is
  // explicitly described as representative in the rendered alt text.
  pushCandidate(candidates, TYPE_IMAGES["plush bear"], "global_fallback");
  candidates.push({ src: null, source: "placeholder", generic: true });
  return candidates;
}

export function resolveProductImage(product) {
  return resolveProductImageCandidates(product)[0];
}

export function imageForProduct(product) {
  return resolveProductImage(product).src;
}

export function imageForDepartment(department) {
  return DEPARTMENT_IMAGES[String(department || "").toLowerCase()] || null;
}
