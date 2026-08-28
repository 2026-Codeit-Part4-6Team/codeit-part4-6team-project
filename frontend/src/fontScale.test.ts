import { describe, expect, it } from "vitest";

import { applyFontScale, readFontScale, saveFontScale, type FontScale } from "./fontScale";

function storage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  };
}

describe("font scale preferences", () => {
  it("falls back to default and ignores unknown saved values", () => {
    const store = storage();
    expect(readFontScale(store)).toBe("default");
    store.setItem("salesbooster.font-scale", "huge");
    expect(readFontScale(store)).toBe("default");
  });

  it.each<FontScale>(["default", "large", "xlarge"])("persists %s", (scale) => {
    const store = storage();
    saveFontScale(scale, store);
    expect(readFontScale(store)).toBe(scale);
  });

  it("applies the selected scale to the document root", () => {
    const root = { dataset: {} as DOMStringMap };
    applyFontScale("large", root);
    expect(root.dataset.fontScale).toBe("large");
  });
});
