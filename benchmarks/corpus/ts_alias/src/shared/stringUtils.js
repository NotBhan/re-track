// benchmarks/corpus/ts_alias/src/shared/stringUtils.js
// Standard JavaScript ESM module

export const DEFAULT_PREFIX = "NODE";

export function formatLabel(name, id) {
  const safeName = String(name || "").trim();
  const safeId = String(id || "0");
  return `${DEFAULT_PREFIX}-${safeName.toUpperCase()}-${safeId}`;
}

export function parseLabel(label) {
  if (!label || typeof label !== "string") {
    return { prefix: "", name: "", id: "" };
  }
  const parts = label.split("-");
  return {
    prefix: parts[0] || "",
    name: parts[1] || "",
    id: parts[2] || "",
  };
}
