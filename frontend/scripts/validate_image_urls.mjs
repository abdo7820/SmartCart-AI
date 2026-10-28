import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../src/productImages.js", import.meta.url), "utf8");
const ids = [...source.matchAll(/PHOTO\("([^"]+)"\)/g)].map((match) => match[1]);
const urls = [...new Set(ids)].map((id) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=900&q=82`);
const timeoutMs = 10000;

async function validate(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { redirect: "follow", signal: controller.signal, headers: { accept: "image/avif,image/webp,image/*,*/*;q=0.8" } });
    const contentType = response.headers.get("content-type") || "";
    await response.body?.cancel();
    return { url, status: response.status, contentType, ok: response.ok && contentType.toLowerCase().startsWith("image/") };
  } catch (error) {
    return { url, status: 0, contentType: "", ok: false, error: error.name === "AbortError" ? "timeout" : error.message };
  } finally {
    clearTimeout(timer);
  }
}

const results = [];
for (const url of urls) results.push(await validate(url));
for (const result of results) console.log(JSON.stringify(result));
const failures = results.filter((result) => !result.ok);
console.log(JSON.stringify({ checked: results.length, failures: failures.length }));
if (failures.length) process.exitCode = 1;
