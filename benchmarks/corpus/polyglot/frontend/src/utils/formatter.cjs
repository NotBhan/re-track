// benchmarks/corpus/polyglot/frontend/src/utils/formatter.cjs
// CommonJS utility module

function formatValue(value, decimals = 2) {
  if (typeof value !== "number") {
    return "0.00";
  }
  return value.toFixed(decimals);
}

function truncateString(str, maxLength = 30) {
  if (!str || str.length <= maxLength) {
    return str || "";
  }
  return str.slice(0, maxLength) + "...";
}

module.exports = {
  formatValue,
  truncateString,
};
