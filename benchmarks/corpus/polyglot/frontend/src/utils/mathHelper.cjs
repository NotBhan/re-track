// benchmarks/corpus/polyglot/frontend/src/utils/mathHelper.cjs
// CommonJS module utilizing require and module.exports

const formatter = require("./formatter.cjs");

function computeTotal(items, discountRatio = 0.0) {
  if (!Array.isArray(items)) {
    return "0.00";
  }
  const rawSum = items.reduce((acc, curr) => acc + (curr.value || 0), 0);
  const discounted = rawSum * (1.0 - discountRatio);
  return formatter.formatValue(discounted, 2);
}

function calculateAverage(numbers) {
  if (!Array.isArray(numbers) || numbers.length === 0) {
    return 0;
  }
  const sum = numbers.reduce((acc, val) => acc + val, 0);
  return sum / numbers.length;
}

module.exports = {
  computeTotal,
  calculateAverage,
};
