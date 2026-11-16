import test from "node:test";
import assert from "node:assert/strict";

// Expo Router 57 uses query-string's CommonJS namespace API.
const query = require("query-string") as {
  parse: (input: string) => Record<string, unknown>;
  stringify: (input: Record<string, string>) => string;
};
test("router query decoder preserves UTF-8, decimal strings and malformed input handling", () => {
  assert.equal(
    query.parse("nombre=Jitomate%20org%C3%A1nico").nombre,
    "Jitomate orgánico",
  );
  assert.equal(query.stringify({ cantidad: "0.200000" }), "cantidad=0.200000");
  assert.equal(query.parse("valor=%2520").valor, "%20");
  assert.equal(
    typeof query.parse("valor=" + "%FE%FF".repeat(1000)).valor,
    "string",
  );
});
